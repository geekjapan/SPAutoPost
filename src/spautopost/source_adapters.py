"""Source adapter interface and deterministic fixture adapters."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Protocol, cast

from .storage.models import Advisory, Severity, SourceRecord, SourceType

CISA_KEV_CATALOG_URL = "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"
SOURCE_ADAPTER_PARSER_VERSION = "source-adapter-fixture-v1"


class SourceAdapterError(ValueError):
    """Raised when a fixture source item cannot be normalized."""


@dataclass(frozen=True)
class AdapterStatus:
    ok: bool
    code: str = "ok"
    message: str = ""


@dataclass(frozen=True)
class SourceFetchQuery:
    cve_id: str | None = None
    vendor: str | None = None
    product: str | None = None
    published_from: datetime | None = None
    published_to: datetime | None = None
    modified_from: datetime | None = None
    modified_to: datetime | None = None
    url: str | None = None  # Firecrawl adapter 用の URL 指定フィールド


@dataclass(frozen=True)
class SourceDocument:
    source_record: SourceRecord
    raw_payload: Mapping[str, object]


class SourceAdapter(Protocol):
    source_type: SourceType
    source_name: str

    def validate_config(self) -> AdapterStatus: ...

    def fetch(
        self, query: SourceFetchQuery | None = None, *, now: datetime | None = None
    ) -> Sequence[SourceDocument]: ...

    def normalize(
        self, document: SourceDocument, *, now: datetime | None = None
    ) -> Sequence[Advisory]: ...


Normalizer = Callable[[SourceDocument, datetime], Sequence[Advisory]]


@dataclass(frozen=True)
class FixtureSourceAdapter:
    source_type: SourceType
    source_name: str
    raw_items: Sequence[Mapping[str, object]]
    normalizer: Normalizer
    parser_version: str = SOURCE_ADAPTER_PARSER_VERSION

    def validate_config(self) -> AdapterStatus:
        if not self.source_name.strip():
            return AdapterStatus(False, "source_name_missing", "source_name is required")
        if not self.raw_items:
            return AdapterStatus(False, "fixture_empty", "at least one fixture item is required")
        return AdapterStatus(True)

    def fetch(
        self, query: SourceFetchQuery | None = None, *, now: datetime | None = None
    ) -> tuple[SourceDocument, ...]:
        timestamp = _utc_now(now)
        documents: list[SourceDocument] = []
        for raw in self.raw_items:
            if not _matches_query(raw, query):
                continue
            raw_hash = _hash_json(raw)
            source_record = SourceRecord(
                source_record_id=f"{self.source_name}-{raw_hash[:12]}",
                source_type=self.source_type,
                source_name=self.source_name,
                source_url=_optional_text(raw, "source_url") or _optional_text(raw, "url"),
                retrieved_at=timestamp,
                raw_hash=raw_hash,
                parser_version=self.parser_version,
                created_at=timestamp,
                http_status=200,
            )
            documents.append(SourceDocument(source_record=source_record, raw_payload=raw))
        return tuple(documents)

    def normalize(
        self, document: SourceDocument, *, now: datetime | None = None
    ) -> tuple[Advisory, ...]:
        return tuple(self.normalizer(document, _utc_now(now)))


def build_kev_fixture_adapter(raw_items: Sequence[Mapping[str, object]]) -> FixtureSourceAdapter:
    return FixtureSourceAdapter(
        source_type="kev",
        source_name="cisa-kev",
        raw_items=raw_items,
        normalizer=normalize_kev_document,
    )


def build_vendor_advisory_fixture_adapter(
    raw_items: Sequence[Mapping[str, object]],
) -> FixtureSourceAdapter:
    return FixtureSourceAdapter(
        source_type="vendor",
        source_name="vendor-advisory",
        raw_items=raw_items,
        normalizer=normalize_vendor_advisory_document,
    )


def build_feed_fixture_adapter(raw_items: Sequence[Mapping[str, object]]) -> FixtureSourceAdapter:
    return FixtureSourceAdapter(
        source_type="rss",
        source_name="rss-feed",
        raw_items=raw_items,
        normalizer=normalize_feed_document,
    )


def normalize_kev_document(document: SourceDocument, now: datetime) -> tuple[Advisory, ...]:
    raw = document.raw_payload
    cve_id = _required_text(raw, "cveID")
    vendor = _optional_text(raw, "vendorProject")
    product = _optional_text(raw, "product")
    title = _optional_text(raw, "vulnerabilityName") or f"{cve_id} known exploited vulnerability"
    date_added = _date_field(raw, "dateAdded")
    required_action = _optional_text(raw, "requiredAction")
    due_date = _optional_text(raw, "dueDate")
    summary = _joined_text(
        _optional_text(raw, "shortDescription"),
        f"Required action: {required_action}" if required_action else None,
        f"Due date: {due_date}" if due_date else None,
    )
    tags = _tags(
        "kev",
        "known-exploited",
        f"vendor:{vendor}" if vendor else None,
        f"product:{product}" if product else None,
        _ransomware_tag(raw),
    )
    return (
        Advisory(
            advisory_id=f"kev-{cve_id.lower()}",
            title=title,
            summary=summary or title,
            source_record_id=document.source_record.source_record_id,
            created_at=now,
            normalized_at=now,
            published_at=_date_to_datetime(date_added),
            severity="unknown",
            cve_ids=(cve_id,),
            references=(
                {
                    "label": "CISA Known Exploited Vulnerabilities Catalog",
                    "url": CISA_KEV_CATALOG_URL,
                    "type": "kev",
                },
            ),
            tags=tags,
        ),
    )


def normalize_vendor_advisory_document(
    document: SourceDocument, now: datetime
) -> tuple[Advisory, ...]:
    raw = document.raw_payload
    advisory_id = _required_text(raw, "vendor_advisory_id")
    url = _required_text(raw, "url")
    return (
        Advisory(
            advisory_id=f"vendor-{advisory_id}",
            title=_required_text(raw, "title"),
            summary=_required_text(raw, "summary"),
            source_record_id=document.source_record.source_record_id,
            created_at=now,
            normalized_at=now,
            published_at=_datetime_field(raw, "published_at"),
            updated_at=_datetime_field(raw, "updated_at"),
            severity=_severity(raw),
            cve_ids=_text_sequence(raw, "cve_ids"),
            vendor_advisory_ids=(advisory_id,),
            references=({"label": "Vendor advisory", "url": url, "type": "vendor"},),
            tags=_tags("vendor-advisory", *_text_sequence(raw, "tags")),
        ),
    )


def normalize_feed_document(document: SourceDocument, now: datetime) -> tuple[Advisory, ...]:
    raw = document.raw_payload
    url = _required_text(raw, "url")
    raw_hash = document.source_record.raw_hash[:12]
    return (
        Advisory(
            advisory_id=f"rss-{raw_hash}",
            title=_required_text(raw, "title"),
            summary=_optional_text(raw, "summary") or _required_text(raw, "title"),
            source_record_id=document.source_record.source_record_id,
            created_at=now,
            normalized_at=now,
            published_at=_datetime_field(raw, "published_at"),
            updated_at=_datetime_field(raw, "updated_at"),
            severity=_severity(raw),
            cve_ids=_text_sequence(raw, "cve_ids"),
            references=({"label": "Feed item", "url": url, "type": "rss"},),
            tags=_tags("feed", *_text_sequence(raw, "tags")),
        ),
    )


def _matches_query(raw: Mapping[str, object], query: SourceFetchQuery | None) -> bool:
    if query is None:
        return True
    cve_ids = {_required_or_optional for _required_or_optional in _raw_cve_ids(raw)}
    if query.cve_id and query.cve_id not in cve_ids:
        return False
    vendor = _optional_text(raw, "vendorProject") or _optional_text(raw, "vendor")
    if query.vendor and vendor != query.vendor:
        return False
    product = _optional_text(raw, "product")
    return not (query.product and product != query.product)


def _raw_cve_ids(raw: Mapping[str, object]) -> tuple[str, ...]:
    cve_id = _optional_text(raw, "cveID")
    if cve_id:
        return (cve_id,)
    return _text_sequence(raw, "cve_ids")


def _required_text(raw: Mapping[str, object], key: str) -> str:
    value = _optional_text(raw, key)
    if value is None:
        raise SourceAdapterError(f"{key} is required")
    return value


def _optional_text(raw: Mapping[str, object], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise SourceAdapterError(f"{key} must be a non-empty string")
    return value.strip()


def _text_sequence(raw: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = raw.get(key)
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise SourceAdapterError(f"{key} must be a list of strings")
    items: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise SourceAdapterError(f"{key}[{index}] must be a non-empty string")
        items.append(item.strip())
    return tuple(items)


def _severity(raw: Mapping[str, object]) -> Severity:
    value = _optional_text(raw, "severity") or "unknown"
    if value not in {"critical", "high", "medium", "low", "unknown"}:
        raise SourceAdapterError("severity is invalid")
    return cast(Severity, value)


def _datetime_field(raw: Mapping[str, object], key: str) -> datetime | None:
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, datetime):
        return _utc_now(value)
    if isinstance(value, str):
        text = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise SourceAdapterError(f"{key} must be an ISO-8601 datetime string") from exc
        return _utc_now(parsed)
    raise SourceAdapterError(f"{key} must be an ISO-8601 datetime string")


def _date_field(raw: Mapping[str, object], key: str) -> date | None:
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise SourceAdapterError(f"{key} must be an ISO-8601 date string") from exc
    raise SourceAdapterError(f"{key} must be an ISO-8601 date string")


def _date_to_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=UTC)


def _joined_text(*parts: str | None) -> str:
    return " ".join(part for part in parts if part)


def _tags(*values: str | None) -> tuple[str, ...]:
    return tuple(value for value in values if value)


def _ransomware_tag(raw: Mapping[str, object]) -> str | None:
    value = _optional_text(raw, "knownRansomwareCampaignUse")
    if not value:
        return None
    return "ransomware:" + value.lower().replace(" ", "-")


def _hash_json(value: Mapping[str, object]) -> str:
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _utc_now(now: datetime | None) -> datetime:
    value = now or datetime.now(UTC)
    if value.tzinfo is None or value.utcoffset() is None:
        raise SourceAdapterError("timestamp must include timezone")
    return value.astimezone(UTC)
