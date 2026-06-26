"""MyJVN / JVN iPedia HND source adapter.

Fetches Japanese vulnerability overview/detail XML from MyJVN and normalizes it
into the existing ``Advisory`` DTO. Transport is injectable so tests never call
live MyJVN; the default transport uses stdlib ``urllib`` over HTTPS only.

正本: GitHub Issue #12 / docs/specs/source-collection.md /
openspec/changes/issue-12-implement-myjvn-adapter/.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol, cast

from .source_adapters import AdapterStatus, SourceDocument, SourceFetchQuery
from .storage.models import Advisory, Severity, SourceRecord

MYJVN_API_URL = "https://jvndb.jvn.jp/myjvn"
MYJVN_DETAIL_URL = "https://jvndb.jvn.jp/ja/contents/"
MYJVN_PARSER_VERSION = "myjvn-hnd-v1"
MYJVN_SOURCE_NAME = "myjvn"
MAX_OVERVIEW_COUNT = 50
MAX_DETAIL_IDS = 10

_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)


class MyjvnAdapterError(RuntimeError):
    """Raised on MyJVN request or parse failures."""


@dataclass(frozen=True)
class MyjvnHttpResponse:
    status: int
    body: str
    headers: Mapping[str, str] = field(default_factory=dict)


class MyjvnTransport(Protocol):
    def __call__(self, url: str, headers: Mapping[str, str]) -> MyjvnHttpResponse: ...


@dataclass(frozen=True)
class MyjvnSourceAdapter:
    """SourceAdapter implementation for MyJVN HND XML."""

    transport: MyjvnTransport
    base_url: str = MYJVN_API_URL
    parser_version: str = MYJVN_PARSER_VERSION
    source_name: str = MYJVN_SOURCE_NAME
    max_overview_count: int = MAX_OVERVIEW_COUNT

    source_type = "myjvn"

    def validate_config(self) -> AdapterStatus:
        if not self.base_url.startswith("https://"):
            return AdapterStatus(False, "base_url_insecure", "base_url must be https")
        if not 1 <= self.max_overview_count <= MAX_OVERVIEW_COUNT:
            return AdapterStatus(
                False,
                "max_overview_count_invalid",
                f"max_overview_count must be 1..{MAX_OVERVIEW_COUNT}",
            )
        return AdapterStatus(True)

    def fetch(
        self, query: SourceFetchQuery | None = None, *, now: datetime | None = None
    ) -> tuple[SourceDocument, ...]:
        timestamp = _utc_now(now)
        params = self._overview_params(query)
        return tuple(self._to_document(item, timestamp) for item in self._collect_overviews(params))

    def fetch_detail(
        self, jvn_ids: Sequence[str], *, now: datetime | None = None
    ) -> tuple[SourceDocument, ...]:
        ids = _jvn_ids_param(jvn_ids)
        timestamp = _utc_now(now)
        documents: list[SourceDocument] = []
        for chunk in _chunks(ids, MAX_DETAIL_IDS):
            params = {
                "method": "getVulnDetailInfo",
                "feed": "hnd",
                "lang": "ja",
                "vulnId": "+".join(chunk),
                "maxCountItem": str(MAX_DETAIL_IDS),
            }
            body = self._request(_build_url(self.base_url, params)).body
            root = _parse_xml(body)
            _raise_for_status(root)
            documents.extend(self._to_document(item, timestamp) for item in _detail_items(root))
        return tuple(documents)

    def normalize(
        self, document: SourceDocument, *, now: datetime | None = None
    ) -> tuple[Advisory, ...]:
        timestamp = _utc_now(now)
        raw = document.raw_payload
        jvn_id = _require_str(raw, "jvn_id")
        cvss = _cvss(raw)
        return (
            Advisory(
                advisory_id=f"myjvn-{jvn_id.lower()}",
                title=_require_str(raw, "title"),
                summary=_require_str(raw, "summary"),
                source_record_id=document.source_record.source_record_id,
                created_at=timestamp,
                normalized_at=timestamp,
                published_at=_myjvn_datetime(raw.get("published_at")),
                updated_at=_myjvn_datetime(raw.get("updated_at")),
                severity=cvss.severity if cvss else "unknown",
                cve_ids=_text_tuple(raw, "cve_ids"),
                jvn_ids=(jvn_id,),
                cvss_version=cvss.version if cvss else None,
                cvss_score=cvss.score if cvss else None,
                cvss_vector=cvss.vector if cvss else None,
                references=_references(raw),
                tags=_tags("myjvn", *_product_tags(raw)),
            ),
        )

    def _overview_params(self, query: SourceFetchQuery | None) -> dict[str, str]:
        params = {
            "method": "getVulnOverviewList",
            "feed": "hnd",
            "lang": "ja",
            "maxCountItem": str(self.max_overview_count),
        }
        if query is None:
            return params
        if query.cve_id:
            params["keyword"] = query.cve_id
        if query.vendor and query.product:
            params["cpeName"] = f"cpe:/*:{query.vendor}:{query.product}"
        params.update(_date_params("dateFirstPublished", query.published_from, query.published_to))
        params.update(_date_params("datePublished", query.modified_from, query.modified_to))
        if query.published_from or query.published_to:
            params["rangeDateFirstPublished"] = "n"
        if query.modified_from or query.modified_to:
            params["rangeDatePublished"] = "n"
        return params

    def _collect_overviews(self, params: Mapping[str, str]) -> tuple[Mapping[str, object], ...]:
        items: list[Mapping[str, object]] = []
        start = 1
        while True:
            page = {**params, "startItem": str(start)}
            body = self._request(_build_url(self.base_url, page)).body
            root = _parse_xml(body)
            status = _raise_for_status(root)
            page_items = _overview_items(root)
            items.extend(page_items)
            total = _status_int(status, "totalRes", len(items))
            returned = _status_int(status, "totalResRet", len(page_items))
            if not page_items or returned <= 0 or len(items) >= total:
                break
            start += returned
        return tuple(items)

    def _request(self, url: str) -> MyjvnHttpResponse:
        response = self.transport(url, {})
        if response.status != 200:
            raise MyjvnAdapterError(f"MyJVN request failed with HTTP {response.status}")
        return response

    def _to_document(self, item: Mapping[str, object], timestamp: datetime) -> SourceDocument:
        jvn_id = _require_str(item, "jvn_id")
        raw_hash = _hash_json(item)
        source_record = SourceRecord(
            source_record_id=f"myjvn-{jvn_id.lower()}-{raw_hash[:12]}",
            source_type="myjvn",
            source_name=self.source_name,
            source_url=_optional_str(item, "source_url") or _detail_url(jvn_id),
            retrieved_at=timestamp,
            raw_hash=raw_hash,
            parser_version=self.parser_version,
            created_at=timestamp,
            http_status=200,
        )
        return SourceDocument(source_record=source_record, raw_payload=item)


@dataclass(frozen=True)
class _Cvss:
    version: str
    score: float
    vector: str | None
    severity: Severity


def urllib_transport(url: str, headers: Mapping[str, str]) -> MyjvnHttpResponse:
    """Default real transport using stdlib ``urllib`` over HTTPS only."""
    if not url.startswith("https://"):
        raise MyjvnAdapterError("MyJVN transport requires an https URL")
    request = urllib.request.Request(url, headers=dict(headers))  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            body = response.read().decode(response.headers.get_content_charset() or "utf-8")
            return MyjvnHttpResponse(
                status=response.status,
                body=body,
                headers={key: value for key, value in response.headers.items()},
            )
    except urllib.error.HTTPError as exc:
        return MyjvnHttpResponse(
            status=exc.code,
            body=exc.read().decode("utf-8", errors="replace"),
            headers={key: value for key, value in (exc.headers or {}).items()},
        )
    except urllib.error.URLError as exc:
        raise MyjvnAdapterError(f"MyJVN transport failed: {exc.reason}") from exc


def _overview_items(root: ET.Element) -> tuple[Mapping[str, object], ...]:
    return tuple(_overview_item(node) for node in root.iter() if _local_name(node.tag) == "item")


def _overview_item(node: ET.Element) -> Mapping[str, object]:
    refs = _overview_references(node)
    cve_ids = _cve_ids(refs)
    jvn_id = _first_text(node, "identifier") or _jvn_from_url(_first_text(node, "link"))
    if jvn_id is None:
        raise MyjvnAdapterError("MyJVN overview item is missing JVN ID")
    return {
        "kind": "overview",
        "jvn_id": jvn_id,
        "title": _required_first_text(node, "title"),
        "summary": _required_first_text(node, "description"),
        "source_url": _first_text(node, "link") or _detail_url(jvn_id),
        "published_at": _first_text(node, "issued"),
        "updated_at": _first_text(node, "modified") or _first_text(node, "date"),
        "cve_ids": cve_ids,
        "references": _prepend_jvn_reference(jvn_id, refs),
        "cvss": _overview_cvss(node),
        "products": _overview_products(node),
    }


def _detail_items(root: ET.Element) -> tuple[Mapping[str, object], ...]:
    return tuple(_detail_item(node) for node in root.iter() if _local_name(node.tag) == "Vulinfo")


def _detail_item(node: ET.Element) -> Mapping[str, object]:
    jvn_id = _required_first_text(node, "VulinfoID")
    refs = _detail_references(node)
    overview = _detail_overview(node)
    mitigation = _joined_text(*_texts_under(node, "Solution", "Description"))
    summary = _joined_text(overview, f"対策: {mitigation}" if mitigation else None)
    return {
        "kind": "detail",
        "jvn_id": jvn_id,
        "title": _required_first_text(node, "Title"),
        "summary": summary or _required_first_text(node, "Title"),
        "source_url": _detail_url(jvn_id),
        "published_at": _first_text(node, "DateFirstPublished"),
        "updated_at": _first_text(node, "DateLastUpdated"),
        "cve_ids": _cve_ids(refs),
        "references": _prepend_jvn_reference(jvn_id, refs),
        "cvss": _detail_cvss(node),
        "products": _detail_products(node),
    }


def _detail_overview(node: ET.Element) -> str | None:
    return _joined_text(*_texts_under(node, "VulinfoDescription", "Overview")) or _joined_text(
        *_texts_under(node, "Overview", "Description")
    )


def _overview_references(node: ET.Element) -> tuple[Mapping[str, str], ...]:
    refs: list[Mapping[str, str]] = []
    for child in node.iter():
        if _local_name(child.tag) != "references":
            continue
        url = _text(child)
        if url is None:
            continue
        ref_type = "cve" if _optional_attr(child, "id", "").upper().startswith("CVE-") else "jvn"
        refs.append(
            {
                "label": _optional_attr(child, "title", "")
                or _optional_attr(child, "id", "")
                or _optional_attr(child, "source", "")
                or "MyJVN reference",
                "url": url,
                "type": ref_type,
            }
        )
    return tuple(refs)


def _detail_references(node: ET.Element) -> tuple[Mapping[str, str], ...]:
    refs: list[Mapping[str, str]] = []
    for item in node.iter():
        if _local_name(item.tag) != "RelatedItem":
            continue
        url = _first_text(item, "URL")
        if url is None:
            continue
        ref_id = _optional_attr(item, "id", "") or _first_text(item, "VulinfoID") or ""
        label = _optional_attr(item, "title", "") or _first_text(item, "Title") or ref_id
        refs.append(
            {
                "label": label or "MyJVN reference",
                "url": url,
                "type": "cve" if ref_id.upper().startswith("CVE-") else "jvn",
            }
        )
    return tuple(refs)


def _prepend_jvn_reference(
    jvn_id: str, refs: Sequence[Mapping[str, str]]
) -> tuple[Mapping[str, str], ...]:
    return (
        {"label": "JVN iPedia", "url": _detail_url(jvn_id), "type": "jvn"},
        *refs,
    )


def _overview_cvss(node: ET.Element) -> Mapping[str, object] | None:
    for child in node.iter():
        if _local_name(child.tag) == "cvss":
            return {
                "version": _optional_attr(child, "version", ""),
                "score": _optional_attr(child, "score", ""),
                "severity": _optional_attr(child, "severity", ""),
                "vector": _optional_attr(child, "vector", ""),
            }
    return None


def _detail_cvss(node: ET.Element) -> Mapping[str, object] | None:
    for child in node.iter():
        name = _local_name(child.tag)
        if name not in {"Cvss", "CvssItem"}:
            continue
        score = _optional_attr(child, "score", "") or _first_text(child, "Base")
        if not score:
            continue
        severity = _optional_attr(child, "severity", "") or _first_text(child, "Severity") or ""
        return {
            "version": _optional_attr(child, "version", ""),
            "score": score,
            "severity": severity,
            "vector": _optional_attr(child, "vector", "") or _first_text(child, "Vector") or "",
        }
    return None


def _overview_products(node: ET.Element) -> tuple[Mapping[str, str], ...]:
    products: list[Mapping[str, str]] = []
    for child in node.iter():
        if _local_name(child.tag) != "cpe":
            continue
        vendor = _optional_attr(child, "vendor", "")
        product = _optional_attr(child, "product", "")
        if vendor or product:
            products.append({"vendor": vendor, "product": product})
    return tuple(products)


def _detail_products(node: ET.Element) -> tuple[Mapping[str, str], ...]:
    products: list[Mapping[str, str]] = []
    for item in node.iter():
        if _local_name(item.tag) != "AffectedItem":
            continue
        vendor = _first_text(item, "Name") or ""
        product = _first_text(item, "ProductName") or ""
        if vendor or product:
            products.append({"vendor": vendor, "product": product})
    return tuple(products)


def _product_tags(raw: Mapping[str, object]) -> tuple[str, ...]:
    products = raw.get("products")
    if not isinstance(products, Sequence) or isinstance(products, (str, bytes)):
        return ()
    tags: list[str] = []
    seen: set[str] = set()
    for product in products:
        if not isinstance(product, Mapping):
            continue
        for prefix, key in (("vendor", "vendor"), ("product", "product")):
            value = product.get(key)
            if not isinstance(value, str) or not value.strip():
                continue
            tag = f"{prefix}:{value.strip()}"
            if tag not in seen:
                seen.add(tag)
                tags.append(tag)
    return tuple(tags)


def _cvss(raw: Mapping[str, object]) -> _Cvss | None:
    cvss = raw.get("cvss")
    if not isinstance(cvss, Mapping):
        return None
    version = _optional_str(cvss, "version") or "unknown"
    score_text = _optional_str(cvss, "score")
    if score_text is None:
        return None
    try:
        score = float(score_text)
    except ValueError:
        return None
    return _Cvss(
        version=version,
        score=score,
        vector=_optional_str(cvss, "vector"),
        severity=_map_severity(_optional_str(cvss, "severity"), score),
    )


def _references(raw: Mapping[str, object]) -> tuple[Mapping[str, str], ...]:
    refs = raw.get("references")
    if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes)):
        return ()
    result: list[Mapping[str, str]] = []
    for ref in refs:
        if not isinstance(ref, Mapping):
            continue
        label = ref.get("label")
        url = ref.get("url")
        ref_type = ref.get("type")
        if isinstance(label, str) and isinstance(url, str) and isinstance(ref_type, str):
            result.append({"label": label, "url": url, "type": ref_type})
    return tuple(result)


def _cve_ids(refs: Sequence[Mapping[str, str]]) -> tuple[str, ...]:
    ids: list[str] = []
    seen: set[str] = set()
    for ref in refs:
        haystack = " ".join(ref.values())
        for match in _CVE_RE.findall(haystack):
            cve_id = match.upper()
            if cve_id not in seen:
                seen.add(cve_id)
                ids.append(cve_id)
    return tuple(ids)


def _date_params(prefix: str, start: datetime | None, end: datetime | None) -> dict[str, str]:
    if start is None and end is None:
        return {}
    if start is None or end is None:
        raise MyjvnAdapterError(f"{prefix} date range requires both a start and an end")
    start_date = _utc_now(start).date()
    end_date = _utc_now(end).date()
    if end_date < start_date:
        raise MyjvnAdapterError(f"{prefix} date range end must not precede start")
    return {
        f"{prefix}StartY": f"{start_date.year:04d}",
        f"{prefix}StartM": f"{start_date.month:02d}",
        f"{prefix}StartD": f"{start_date.day:02d}",
        f"{prefix}EndY": f"{end_date.year:04d}",
        f"{prefix}EndM": f"{end_date.month:02d}",
        f"{prefix}EndD": f"{end_date.day:02d}",
    }


def _build_url(base_url: str, params: Mapping[str, str]) -> str:
    query = "&".join(f"{key}={_quote(value)}" for key, value in sorted(params.items()))
    return f"{base_url}?{query}" if query else base_url


def _quote(value: str) -> str:
    return urllib.parse.quote(value, safe=",:/+*")


def _jvn_ids_param(jvn_ids: Sequence[str]) -> tuple[str, ...]:
    ids = tuple(value.strip() for value in jvn_ids if isinstance(value, str) and value.strip())
    if not ids:
        raise MyjvnAdapterError("at least one JVN ID is required")
    return ids


def _chunks(values: Sequence[str], size: int) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(values[index : index + size]) for index in range(0, len(values), size))


def _parse_xml(raw: str) -> ET.Element:
    try:
        return ET.fromstring(raw)  # noqa: S314
    except ET.ParseError as exc:
        raise MyjvnAdapterError("MyJVN response is not valid XML") from exc


def _raise_for_status(root: ET.Element) -> ET.Element | None:
    for node in root.iter():
        if _local_name(node.tag) != "Status":
            continue
        if node.attrib.get("retCd", "0").strip() == "0":
            return node
        message = node.attrib.get("errMsg") or node.attrib.get("errCd") or "MyJVN status error"
        raise MyjvnAdapterError(message)
    return None


def _status_int(status: ET.Element | None, key: str, default: int) -> int:
    if status is None:
        return default
    try:
        return int(status.attrib.get(key, str(default)))
    except ValueError:
        return default


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_text(node: ET.Element, name: str) -> str | None:
    for child in node.iter():
        if _local_name(child.tag) == name:
            return _text(child)
    return None


def _required_first_text(node: ET.Element, name: str) -> str:
    value = _first_text(node, name)
    if value is None:
        raise MyjvnAdapterError(f"{name} is required")
    return value


def _texts_under(node: ET.Element, ancestor_name: str, child_name: str) -> tuple[str, ...]:
    values: list[str] = []
    for ancestor in node.iter():
        if _local_name(ancestor.tag) != ancestor_name:
            continue
        for child in ancestor.iter():
            if _local_name(child.tag) == child_name:
                value = _text(child)
                if value:
                    values.append(value)
    return tuple(values)


def _text(node: ET.Element) -> str | None:
    if node.text is None:
        return None
    value = " ".join(node.text.split())
    return value or None


def _optional_attr(node: ET.Element, key: str, default: str) -> str:
    value = node.attrib.get(key, default).strip()
    return value


def _jvn_from_url(url: str | None) -> str | None:
    if url is None:
        return None
    match = re.search(r"JVNDB-\d{4}-\d{6}", url, re.IGNORECASE)
    return match.group(0).upper() if match else None


def _detail_url(jvn_id: str) -> str:
    parts = jvn_id.split("-")
    if len(parts) >= 3:
        return f"{MYJVN_DETAIL_URL}{parts[1]}/{jvn_id}.html"
    return f"https://jvndb.jvn.jp/ja/contents/{jvn_id}.html"


def _myjvn_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise MyjvnAdapterError("MyJVN datetime must be a string")
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise MyjvnAdapterError(f"invalid MyJVN datetime: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _map_severity(text: str | None, score: float) -> Severity:
    if text:
        normalized = text.strip().lower()
        if normalized in {"critical", "high", "medium", "low"}:
            return cast("Severity", normalized)
        if normalized in {"緊急"}:
            return "critical"
        if normalized in {"重要"}:
            return "high"
        if normalized in {"警告"}:
            return "medium"
        if normalized in {"注意"}:
            return "low"
    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 4.0:
        return "medium"
    if score > 0:
        return "low"
    return "unknown"


def _text_tuple(raw: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = raw.get(key)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item)


def _joined_text(*values: str | None) -> str:
    return "\n".join(value for value in values if value)


def _require_str(raw: Mapping[str, object], key: str) -> str:
    value = _optional_str(raw, key)
    if value is None:
        raise MyjvnAdapterError(f"{key} is required")
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
        raise MyjvnAdapterError("timestamp must include timezone")
    return value.astimezone(UTC)


__all__ = [
    "MYJVN_API_URL",
    "MYJVN_PARSER_VERSION",
    "MyjvnAdapterError",
    "MyjvnHttpResponse",
    "MyjvnSourceAdapter",
    "MyjvnTransport",
    "urllib_transport",
]
