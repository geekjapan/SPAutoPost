"""ストレージポートが受け渡す frozen-dataclass DTO。

正本: docs/specs/data-model.md / docs/specs/audit-log.md /
docs/specs/sharepoint-publishing.md と本 change の spec。

方針:
- frozen-dataclass で不変。Secret（API key / token / client secret 等）を保持しない。
- 全 timestamp は tz-aware UTC。naive datetime は境界で ``ConstraintViolationError``。
- ``draft_posts.summary_for_users`` / ``draft_posts.impact`` /
  ``publications.idempotency_key`` は非 Optional（必須）。
- ``event_type`` は audit-log.md の 15 値 Literal。status / operation 等も Literal で型付け。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields
from datetime import UTC, datetime
from typing import Literal, get_args

from .errors import ConstraintViolationError

# --- enum 型（Literal で表現） ---------------------------------------------

SourceType = Literal["manual", "nvd", "myjvn", "kev", "vendor", "rss", "external_collector", "web_scrape"]

Severity = Literal["critical", "high", "medium", "low", "unknown"]

DraftStatus = Literal[
    "created",
    "generated",
    "review_requested",
    "reviewed",
    "approved",
    "rejected",
    "regeneration_requested",
    "publishing",
    "published",
    "failed",
    "cancelled",
]

Audience = Literal["general_users", "administrators", "mixed"]
Urgency = Literal["emergency", "high", "normal", "low"]

ReviewAction = Literal["request_review", "comment", "approve", "reject", "request_regeneration"]

TargetType = Literal["list-item", "site-page"]

PublicationStatus = Literal["pending", "dry_run", "publishing", "published", "failed", "skipped"]

PublicationOperation = Literal["dry-run", "create", "update", "publish"]

AdminCommandType = Literal["edit", "approve", "reject", "request_regeneration", "publish_request"]

AdminCommandStatus = Literal["pending", "processing", "succeeded", "failed", "cancelled"]

# audit-log.md の 15 値（本 change の正本）。
AuditEventType = Literal[
    "source_fetch",
    "source_parse",
    "normalize",
    "triage",
    "draft_generate",
    "draft_validate",
    "review",
    "approve",
    "reject",
    "regenerate",
    "publish_dry_run",
    "publish_create",
    "publish_update",
    "publish_result",
    "error",
]

AuditResult = Literal["success", "failure", "skipped", "warning"]

# CHECK 制約 / backend で参照する正本の値集合（schema 等価テストで利用）。
AUDIT_EVENT_TYPES: tuple[str, ...] = get_args(AuditEventType)
DRAFT_STATUSES: tuple[str, ...] = get_args(DraftStatus)
PUBLICATION_STATUSES: tuple[str, ...] = get_args(PublicationStatus)
PUBLICATION_OPERATIONS: tuple[str, ...] = get_args(PublicationOperation)
REVIEW_ACTIONS: tuple[str, ...] = get_args(ReviewAction)
SOURCE_TYPES: tuple[str, ...] = get_args(SourceType)
TARGET_TYPES: tuple[str, ...] = get_args(TargetType)
ADMIN_COMMAND_TYPES: tuple[str, ...] = get_args(AdminCommandType)
ADMIN_COMMAND_STATUSES: tuple[str, ...] = get_args(AdminCommandStatus)

_SECRET_KEY_FRAGMENTS: tuple[str, ...] = (
    "api_key",
    "apikey",
    "access_token",
    "refreshtoken",
    "refresh_token",
    "client_secret",
    "private_key",
    "password",
    "cookie",
    "authorization",
)


# --- tz-aware UTC 境界検査 -------------------------------------------------


def ensure_utc(value: datetime, field_name: str) -> datetime:
    """tz-aware UTC datetime を強制する。

    naive datetime（tzinfo 無し）は ``ConstraintViolationError``。tz-aware だが
    UTC でないものは UTC に正規化して返す（不変方針のため新しい値を返す）。
    """
    if value.tzinfo is None or value.utcoffset() is None:
        raise ConstraintViolationError(
            f"{field_name} must be timezone-aware UTC; got naive datetime"
        )
    return value.astimezone(UTC)


def _validate_timestamps(instance: object) -> None:
    """dataclass の datetime フィールドを境界で tz-aware UTC に検査・正規化する。

    frozen-dataclass なので ``object.__setattr__`` で正規化値を書き戻す。
    """
    for f in fields(instance):  # type: ignore[arg-type]
        raw = getattr(instance, f.name)
        if isinstance(raw, datetime):
            object.__setattr__(instance, f.name, ensure_utc(raw, f.name))


def _contains_secret_key(value: object) -> bool:
    """JSON-like value に secret 由来の key が含まれるか再帰的に検査する。"""
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(fragment in normalized for fragment in _SECRET_KEY_FRAGMENTS):
                return True
            if _contains_secret_key(nested):
                return True
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_secret_key(item) for item in value)
    return False


# --- DTO -------------------------------------------------------------------


@dataclass(frozen=True)
class SourceRecord:
    """外部情報源または手動入力から取得した生データの記録（ルートエンティティ）。"""

    source_record_id: str
    source_type: SourceType
    source_name: str
    retrieved_at: datetime
    raw_hash: str
    parser_version: str
    created_at: datetime
    source_url: str | None = None
    raw_payload_ref: str | None = None
    http_status: int | None = None
    etag: str | None = None
    last_modified: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        _validate_timestamps(self)


@dataclass(frozen=True)
class Advisory:
    """脆弱性・セキュリティ注意喚起の正規化データ。"""

    advisory_id: str
    title: str
    summary: str
    created_at: datetime
    normalized_at: datetime
    source_record_id: str | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = None
    severity: Severity = "unknown"
    cve_ids: Sequence[str] = ()
    jvn_ids: Sequence[str] = ()
    vendor_advisory_ids: Sequence[str] = ()
    cvss_version: str | None = None
    cvss_score: float | None = None
    cvss_vector: str | None = None
    references: Sequence[Mapping[str, str]] = ()
    tags: Sequence[str] = ()

    def __post_init__(self) -> None:
        _validate_timestamps(self)


@dataclass(frozen=True)
class DraftPost:
    """SharePoint 掲示板向けの原稿。

    ``summary_for_users`` / ``impact`` は非 Optional（必須）。
    """

    draft_id: str
    title: str
    audience: Audience
    urgency: Urgency
    summary_for_users: str
    impact: str
    status: DraftStatus
    created_at: datetime
    updated_at: datetime
    advisory_id: str | None = None
    advisory_ids: Sequence[str] = ()
    required_actions: Sequence[str] = ()
    admin_actions: Sequence[str] = ()
    references: Sequence[Mapping[str, str]] = ()
    deadline: datetime | None = None
    generated_by_provider: str | None = None
    prompt_version: str | None = None
    generation_input_hash: str | None = None
    validation_warnings: Sequence[str] = ()
    reviewer: str | None = None
    review_comments: Sequence[str] = ()

    def __post_init__(self) -> None:
        _validate_timestamps(self)


@dataclass(frozen=True)
class ReviewEvent:
    """レビューと承認の履歴（append-only）。"""

    review_event_id: str
    draft_id: str
    reviewer: str
    action: ReviewAction
    created_at: datetime
    comment: str | None = None
    previous_status: DraftStatus | None = None
    next_status: DraftStatus | None = None

    def __post_init__(self) -> None:
        _validate_timestamps(self)


@dataclass(frozen=True)
class Publication:
    """SharePoint 投稿の結果。

    ``idempotency_key`` は非 Optional（必須）。null / 空白のみは境界で拒否する。
    汎用 ``page_id`` 列は持たない（spec 名称の列のみ）。
    """

    publication_id: str
    draft_id: str
    target_type: TargetType
    target_site_id: str
    publication_status: PublicationStatus
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
    target_list_id: str | None = None
    target_page_library_id: str | None = None
    sharepoint_item_id: str | None = None
    sharepoint_page_id: str | None = None
    operation: PublicationOperation | None = None
    published_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool | None = None

    def __post_init__(self) -> None:
        _validate_timestamps(self)
        if not self.idempotency_key or not self.idempotency_key.strip():
            raise ConstraintViolationError(
                "publications.idempotency_key must be a non-empty, non-blank string"
            )


@dataclass(frozen=True)
class AuditEvent:
    """監査・障害対応・説明責任のためのイベント（append-only）。"""

    audit_event_id: str
    event_type: AuditEventType
    correlation_id: str
    result: AuditResult
    created_at: datetime
    actor: str | None = None
    service_principal: str | None = None
    related_ids: Mapping[str, object] | None = None
    source_name: str | None = None
    provider_name: str | None = None
    provider_type: str | None = None
    prompt_version: str | None = None
    target_site_id: str | None = None
    target_list_id: str | None = None
    target_page_library_id: str | None = None
    sharepoint_item_id: str | None = None
    sharepoint_page_id: str | None = None
    idempotency_key: str | None = None
    operation: PublicationOperation | None = None
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        _validate_timestamps(self)
        if self.event_type not in AUDIT_EVENT_TYPES:
            raise ConstraintViolationError(
                f"audit_events.event_type must be one of the 15 audit-log values; "
                f"got {self.event_type!r}"
            )


@dataclass(frozen=True)
class AdminCommand:
    """Admin UI/API から Python core への非同期 command inbox。

    payload は Secret を保持してはならない。storage 境界で secret 由来の key を
    検出した場合は保存せず ``ConstraintViolationError`` を送出する。
    """

    command_id: str
    command_type: AdminCommandType
    idempotency_key: str
    created_at: datetime
    target_draft_id: str | None = None
    requested_by: str | None = None
    payload: Mapping[str, object] = field(default_factory=dict)
    status: AdminCommandStatus = "pending"
    error_code: str | None = None
    error_message: str | None = None
    correlation_id: str | None = None
    processed_at: datetime | None = None

    def __post_init__(self) -> None:
        _validate_timestamps(self)
        if not self.idempotency_key or not self.idempotency_key.strip():
            raise ConstraintViolationError(
                "admin_commands.idempotency_key must be a non-empty, non-blank string"
            )
        if _contains_secret_key(self.payload):
            raise ConstraintViolationError("admin_commands.payload must not contain secret keys")
