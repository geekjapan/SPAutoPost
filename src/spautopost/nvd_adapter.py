"""NVD CVE API 2.0 source adapter.

Fetches CVE records from the NVD CVE API 2.0 and normalizes them into the
existing ``Advisory`` DTO. The transport is injectable so unit/fixture tests
never call live NVD. A default stdlib ``urllib`` transport is provided for real
use. Pagination, an explicit rate-limit policy (minimum request interval plus
``Retry-After``-aware retry), and an optional API key (sent only as a request
header, never logged or stored) are handled here.

正本: GitHub Issue #11 / docs/specs/source-collection.md /
openspec/changes/issue-11-implement-nvd-adapter/.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol, cast

from .source_adapters import (
    CISA_KEV_CATALOG_URL,
    AdapterStatus,
    SourceDocument,
    SourceFetchQuery,
)
from .storage.models import Advisory, Severity, SourceRecord

NVD_CVE_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_CVE_DETAIL_URL = "https://nvd.nist.gov/vuln/detail/"
NVD_PARSER_VERSION = "nvd-cve-2.0-v1"
NVD_SOURCE_NAME = "nvd"

MAX_CVE_IDS = 100  # NVD caps cveIds at 100 comma-separated IDs.
MAX_RANGE_DAYS = 120  # NVD caps date-range params at 120 consecutive days.
DEFAULT_RESULTS_PER_PAGE = 2000  # NVD default and maximum.
MAX_RESULTS_PER_PAGE = 2000

# NVD recommends ~6s between requests without an API key (50 req / 30s with key,
# so callers with a key should lower this). Default to the conservative value.
DEFAULT_REQUEST_INTERVAL_SECONDS = 6.0
RETRY_STATUSES: frozenset[int] = frozenset({429, 503})


class NvdAdapterError(RuntimeError):
    """Raised on NVD request, pagination, rate-limit, or parse failures."""


@dataclass(frozen=True)
class NvdHttpResponse:
    """Transport-agnostic HTTP response carrying parsed JSON."""

    status: int
    body: Mapping[str, object]
    headers: Mapping[str, str] = field(default_factory=dict)


class NvdTransport(Protocol):
    def __call__(self, url: str, headers: Mapping[str, str]) -> NvdHttpResponse: ...


@dataclass(frozen=True)
class NvdRateLimitPolicy:
    """Explicit, testable rate-limit policy.

    ``min_interval_seconds`` is waited between successive page requests.
    On a retryable status the ``Retry-After`` header is honored, falling back to
    ``default_retry_after_seconds``. ``sleeper`` is injectable so tests add no
    real delay.
    """

    min_interval_seconds: float = DEFAULT_REQUEST_INTERVAL_SECONDS
    max_retries: int = 3
    default_retry_after_seconds: float = DEFAULT_REQUEST_INTERVAL_SECONDS
    sleeper: Callable[[float], None] = time.sleep
    retry_statuses: frozenset[int] = RETRY_STATUSES


@dataclass(frozen=True)
class NvdSourceAdapter:
    """SourceAdapter implementation for the NVD CVE API 2.0."""

    transport: NvdTransport
    api_key: str | None = None
    base_url: str = NVD_CVE_API_URL
    results_per_page: int = DEFAULT_RESULTS_PER_PAGE
    rate_limit: NvdRateLimitPolicy = field(default_factory=NvdRateLimitPolicy)
    parser_version: str = NVD_PARSER_VERSION
    source_name: str = NVD_SOURCE_NAME

    source_type = "nvd"

    def validate_config(self) -> AdapterStatus:
        if not self.base_url.startswith("https://"):
            return AdapterStatus(False, "base_url_insecure", "base_url must be https")
        if not 1 <= self.results_per_page <= MAX_RESULTS_PER_PAGE:
            return AdapterStatus(
                False,
                "results_per_page_invalid",
                f"results_per_page must be 1..{MAX_RESULTS_PER_PAGE}",
            )
        return AdapterStatus(True)

    def fetch(
        self, query: SourceFetchQuery | None = None, *, now: datetime | None = None
    ) -> tuple[SourceDocument, ...]:
        timestamp = _utc_now(now)
        params = self._build_query_params(query)
        return tuple(self._to_document(item, timestamp) for item in self._collect(params))

    def fetch_cve_ids(
        self, cve_ids: Sequence[str], *, now: datetime | None = None
    ) -> tuple[SourceDocument, ...]:
        """Fetch multiple CVEs in one request (``cveIds``), capped at 100."""
        timestamp = _utc_now(now)
        params = {"cveIds": _cve_ids_param(cve_ids)}
        return tuple(self._to_document(item, timestamp) for item in self._collect(params))

    def normalize(
        self, document: SourceDocument, *, now: datetime | None = None
    ) -> tuple[Advisory, ...]:
        timestamp = _utc_now(now)
        cve = _as_mapping(_as_mapping(document.raw_payload).get("cve"))
        cve_id = _require_str(cve, "id")
        cvss = _primary_cvss(cve)
        is_kev = bool(_optional_str(cve, "cisaExploitAdd"))
        references = _references(cve)
        if is_kev:
            references = (*references, _KEV_REFERENCE)
        tags = _tags(
            "nvd",
            *_cpe_tags(cve),
            *(("kev", "known-exploited") if is_kev else ()),
        )
        advisory = Advisory(
            advisory_id=f"nvd-{cve_id.lower()}",
            title=_optional_str(cve, "cisaVulnerabilityName") or cve_id,
            summary=_english_description(cve) or cve_id,
            source_record_id=document.source_record.source_record_id,
            created_at=timestamp,
            normalized_at=timestamp,
            published_at=_nvd_datetime(cve.get("published")),
            updated_at=_nvd_datetime(cve.get("lastModified")),
            severity=cvss.severity if cvss else "unknown",
            cve_ids=(cve_id,),
            cvss_version=cvss.version if cvss else None,
            cvss_score=cvss.score if cvss else None,
            cvss_vector=cvss.vector if cvss else None,
            references=references,
            tags=tags,
        )
        return (advisory,)

    # --- internals --------------------------------------------------------

    def _build_query_params(self, query: SourceFetchQuery | None) -> dict[str, str]:
        if query is not None and query.cve_id:
            return {"cveIds": _cve_ids_param([query.cve_id])}
        date_params = _date_range_params(query) if query is not None else {}
        if not date_params:
            raise NvdAdapterError("NVD fetch requires a CVE ID or a published/modified date range")
        return date_params

    def _collect(self, params: Mapping[str, str]) -> list[object]:
        collected: list[object] = []
        start_index = 0
        requests_made = 0
        while True:
            if requests_made > 0:
                self.rate_limit.sleeper(self.rate_limit.min_interval_seconds)
            page = {
                **params,
                "startIndex": str(start_index),
                "resultsPerPage": str(self.results_per_page),
            }
            body = self._request(_build_url(self.base_url, page)).body
            vulnerabilities = _as_list(body.get("vulnerabilities"))
            collected.extend(vulnerabilities)
            requests_made += 1
            total = _as_int(body.get("totalResults"), default=len(collected))
            if not vulnerabilities or len(collected) >= total:
                break
            start_index += len(vulnerabilities)
        return collected

    def _request(self, url: str) -> NvdHttpResponse:
        headers = {"apiKey": self.api_key} if self.api_key else {}
        attempts = 0
        while True:
            response = self.transport(url, headers)
            if response.status == 200:
                return response
            if (
                response.status in self.rate_limit.retry_statuses
                and attempts < self.rate_limit.max_retries
            ):
                self.rate_limit.sleeper(
                    _retry_after(response.headers, self.rate_limit.default_retry_after_seconds)
                )
                attempts += 1
                continue
            raise NvdAdapterError(f"NVD request failed with HTTP {response.status}")

    def _to_document(self, item: object, timestamp: datetime) -> SourceDocument:
        cve = _as_mapping(_as_mapping(item).get("cve"))
        cve_id = _require_str(cve, "id")
        raw_hash = _hash_json(cast("Mapping[str, object]", item))
        source_record = SourceRecord(
            source_record_id=f"nvd-{cve_id.lower()}-{raw_hash[:12]}",
            source_type="nvd",
            source_name=self.source_name,
            source_url=f"{NVD_CVE_DETAIL_URL}{cve_id}",
            retrieved_at=timestamp,
            raw_hash=raw_hash,
            parser_version=self.parser_version,
            created_at=timestamp,
            http_status=200,
        )
        return SourceDocument(
            source_record=source_record, raw_payload=cast("Mapping[str, object]", item)
        )


_KEV_REFERENCE: Mapping[str, str] = {
    "label": "CISA Known Exploited Vulnerabilities Catalog",
    "url": CISA_KEV_CATALOG_URL,
    "type": "kev",
}


@dataclass(frozen=True)
class _Cvss:
    version: str
    score: float
    vector: str | None
    severity: Severity


def urllib_transport(url: str, headers: Mapping[str, str]) -> NvdHttpResponse:
    """Default real transport using stdlib ``urllib`` over HTTPS only."""
    if not url.startswith("https://"):
        raise NvdAdapterError("NVD transport requires an https URL")
    request = urllib.request.Request(url, headers=dict(headers))  # noqa: S310 (https enforced)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 (https enforced)
            return NvdHttpResponse(
                status=response.status,
                body=_load_json(response.read()),
                headers={key: value for key, value in response.headers.items()},
            )
    except urllib.error.HTTPError as exc:  # surface status so rate-limit retry can act
        try:
            body = _load_json(exc.read())
        except NvdAdapterError:
            body = {}
        return NvdHttpResponse(
            status=exc.code,
            body=body,
            headers={key: value for key, value in (exc.headers or {}).items()},
        )
    except urllib.error.URLError as exc:
        raise NvdAdapterError(f"NVD transport failed: {exc.reason}") from exc


def _load_json(raw: bytes) -> Mapping[str, object]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise NvdAdapterError("NVD response is not valid JSON") from exc
    return parsed if isinstance(parsed, Mapping) else {}


def _build_url(base_url: str, params: Mapping[str, str]) -> str:
    query = "&".join(f"{key}={_quote(value)}" for key, value in sorted(params.items()))
    return f"{base_url}?{query}" if query else base_url


def _quote(value: str) -> str:
    return urllib.parse.quote(value, safe=",:")


def _cve_ids_param(cve_ids: Sequence[str]) -> str:
    ids = [c.strip() for c in cve_ids if isinstance(c, str) and c.strip()]
    if not ids:
        raise NvdAdapterError("at least one CVE ID is required")
    if len(ids) > MAX_CVE_IDS:
        raise NvdAdapterError(f"at most {MAX_CVE_IDS} CVE IDs per request; got {len(ids)}")
    return ",".join(ids)


def _date_range_params(query: SourceFetchQuery) -> dict[str, str]:
    params: dict[str, str] = {}
    if query.published_from or query.published_to:
        start, end = _validated_range(query.published_from, query.published_to, "published")
        params["pubStartDate"] = _format_nvd_date(start)
        params["pubEndDate"] = _format_nvd_date(end)
    if query.modified_from or query.modified_to:
        start, end = _validated_range(query.modified_from, query.modified_to, "modified")
        params["lastModStartDate"] = _format_nvd_date(start)
        params["lastModEndDate"] = _format_nvd_date(end)
    return params


def _validated_range(
    start: datetime | None, end: datetime | None, label: str
) -> tuple[datetime, datetime]:
    if start is None or end is None:
        raise NvdAdapterError(f"{label} date range requires both a start and an end")
    start_utc, end_utc = _utc_now(start), _utc_now(end)
    if end_utc < start_utc:
        raise NvdAdapterError(f"{label} date range end must not precede start")
    if end_utc - start_utc > timedelta(days=MAX_RANGE_DAYS):
        raise NvdAdapterError(f"{label} date range must not exceed {MAX_RANGE_DAYS} days")
    return start_utc, end_utc


def _format_nvd_date(value: datetime) -> str:
    # NVD ISO-8601 extended; no offset means UTC, which we enforce.
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000")


def _primary_cvss(cve: Mapping[str, object]) -> _Cvss | None:
    metrics = cve.get("metrics")
    if not isinstance(metrics, Mapping):
        return None
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        entries = metrics.get(key)
        if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)) or not entries:
            continue
        entry = _primary_entry(entries)
        data = entry.get("cvssData")
        if not isinstance(data, Mapping):
            continue
        version = _optional_str(data, "version")
        score = data.get("baseScore")
        if version is None or not isinstance(score, (int, float)):
            continue
        severity_text = _optional_str(data, "baseSeverity") or _optional_str(entry, "baseSeverity")
        return _Cvss(
            version=version,
            score=float(score),
            vector=_optional_str(data, "vectorString"),
            severity=_map_severity(severity_text, float(score)),
        )
    return None


def _primary_entry(entries: Sequence[object]) -> Mapping[str, object]:
    mappings = [entry for entry in entries if isinstance(entry, Mapping)]
    for entry in mappings:
        if entry.get("type") == "Primary":
            return entry
    return mappings[0] if mappings else {}


def _map_severity(text: str | None, score: float) -> Severity:
    if text:
        normalized = text.strip().lower()
        if normalized in {"critical", "high", "medium", "low"}:
            return cast("Severity", normalized)
    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 4.0:
        return "medium"
    if score > 0.0:
        return "low"
    return "unknown"


def _english_description(cve: Mapping[str, object]) -> str | None:
    descriptions = cve.get("descriptions")
    if not isinstance(descriptions, Sequence) or isinstance(descriptions, (str, bytes)):
        return None
    fallback: str | None = None
    for item in descriptions:
        if not isinstance(item, Mapping):
            continue
        value = _optional_str(item, "value")
        if value is None:
            continue
        fallback = fallback or value
        if _optional_str(item, "lang") == "en":
            return value
    return fallback


def _references(cve: Mapping[str, object]) -> tuple[Mapping[str, str], ...]:
    references = cve.get("references")
    if not isinstance(references, Sequence) or isinstance(references, (str, bytes)):
        return ()
    result: list[Mapping[str, str]] = []
    for item in references:
        if not isinstance(item, Mapping):
            continue
        url = _optional_str(item, "url")
        if url is None:
            continue
        result.append(
            {"label": _optional_str(item, "source") or "NVD reference", "url": url, "type": "nvd"}
        )
    return tuple(result)


def _cpe_tags(cve: Mapping[str, object]) -> tuple[str, ...]:
    # Surface vendor/product hints from CPE criteria as tags (dedup bounds size).
    # Dedup keeps this small in practice; revisit only if a CVE's CPE set proves
    # large enough to bloat tags.
    tags: list[str] = []
    seen: set[str] = set()
    for criteria in _cpe_criteria(cve):
        parts = criteria.replace(r"\:", "__COLON__").split(":")
        if len(parts) < 5:
            continue
        for prefix, raw in (("vendor", parts[3]), ("product", parts[4])):
            value = raw.replace("__COLON__", ":").strip()
            if not value or value in {"*", "-"}:
                continue
            tag = f"{prefix}:{value}"
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return tuple(tags)


def _cpe_criteria(cve: Mapping[str, object]) -> tuple[str, ...]:
    configurations = cve.get("configurations")
    if not isinstance(configurations, Sequence) or isinstance(configurations, (str, bytes)):
        return ()
    criteria: list[str] = []
    for configuration in configurations:
        if not isinstance(configuration, Mapping):
            continue
        nodes = configuration.get("nodes")
        if not isinstance(nodes, Sequence) or isinstance(nodes, (str, bytes)):
            continue
        stack = list(nodes)
        while stack:
            node = stack.pop()
            if not isinstance(node, Mapping):
                continue
            matches = node.get("cpeMatch")
            if isinstance(matches, Sequence) and not isinstance(matches, (str, bytes)):
                for match in matches:
                    if isinstance(match, Mapping):
                        value = _optional_str(match, "criteria")
                        if value:
                            criteria.append(value)
            children = node.get("children")
            if isinstance(children, Sequence) and not isinstance(children, (str, bytes)):
                stack.extend(children)
    return tuple(criteria)


def _nvd_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise NvdAdapterError("NVD datetime must be a string")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise NvdAdapterError(f"invalid NVD datetime: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _retry_after(headers: Mapping[str, str], default: float) -> float:
    for key, value in headers.items():
        if key.lower() == "retry-after":
            try:
                return max(0.0, float(value))
            except (TypeError, ValueError):
                return default
    return default


def _as_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise NvdAdapterError("expected a JSON object")
    return cast("Mapping[str, object]", value)


def _as_list(value: object) -> list[object]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise NvdAdapterError("expected a JSON array")
    return list(value)


def _as_int(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default


def _require_str(raw: Mapping[str, object], key: str) -> str:
    value = _optional_str(raw, key)
    if value is None:
        raise NvdAdapterError(f"{key} is required")
    return value


def _optional_str(raw: Mapping[str, object], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _tags(*values: str) -> tuple[str, ...]:
    return tuple(value for value in values if value)


def _hash_json(value: Mapping[str, object]) -> str:
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _utc_now(now: datetime | None) -> datetime:
    value = now or datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise NvdAdapterError("timestamp must include timezone")
    return value.astimezone(UTC)


__all__ = [
    "NVD_CVE_API_URL",
    "NVD_PARSER_VERSION",
    "NvdAdapterError",
    "NvdHttpResponse",
    "NvdRateLimitPolicy",
    "NvdSourceAdapter",
    "NvdTransport",
    "urllib_transport",
]
