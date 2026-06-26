"""canonical entity の薄い Python 表現（data-model.md 由来）。

schema 正本は SQL migration。ここは型と enum 値集合を Python 側に与える薄い層で、
``dataclasses.asdict`` で storage port の dict にそのまま渡せる。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# enum 値集合（SQL の CHECK 制約と一致させること）。
SOURCE_TYPES = ("manual", "nvd", "myjvn", "kev", "vendor", "rss", "external_collector")
SEVERITIES = ("critical", "high", "medium", "low", "unknown")
DRAFT_STATUSES = (
    "created", "generated", "review_requested", "reviewed", "approved", "rejected",
    "regeneration_requested", "publishing", "published", "failed", "cancelled",
)
REVIEW_ACTIONS = ("request_review", "comment", "approve", "reject", "request_regeneration")
PUBLICATION_STATUSES = ("pending", "dry_run", "publishing", "published", "failed", "skipped")
AUDIT_EVENT_TYPES = (
    "source_fetch", "normalize", "draft_generate", "validate", "review",
    "approve", "publish", "error",
)
AUDIT_RESULTS = ("success", "failure", "skipped", "warning")
COMMAND_TYPES = ("edit", "approve", "reject", "request_regeneration", "publish_request")
COMMAND_STATUSES = ("pending", "processing", "succeeded", "failed", "cancelled")


@dataclass
class SourceRecord:
    source_record_id: str
    source_type: str
    source_name: str
    retrieved_at: str
    raw_hash: str
    parser_version: str
    source_url: str | None = None


@dataclass
class Advisory:
    advisory_id: str
    title: str
    summary: str
    created_at: str
    normalized_at: str
    source_refs: list = field(default_factory=list)
    references: list = field(default_factory=list)
    cve_ids: list = field(default_factory=list)
    affected_products: list = field(default_factory=list)
    severity: str | None = None
    published_at: str | None = None
    updated_at: str | None = None


@dataclass
class DraftPost:
    draft_id: str
    title: str
    audience: str
    urgency: str
    summary_for_users: str
    impact: str
    status: str
    created_at: str
    updated_at: str
    advisory_ids: list = field(default_factory=list)
    required_actions: list = field(default_factory=list)
    references: list = field(default_factory=list)


@dataclass
class ReviewEvent:
    review_event_id: str
    draft_id: str
    reviewer: str
    action: str
    created_at: str
    comment: str | None = None


@dataclass
class Publication:
    publication_id: str
    draft_id: str
    target_type: str
    target_site_id: str
    publication_status: str
    idempotency_key: str
    created_at: str
    updated_at: str


@dataclass
class AuditEvent:
    audit_event_id: str
    event_type: str
    correlation_id: str
    result: str
    created_at: str
    related_ids: dict = field(default_factory=dict)
    actor: str | None = None
    message: str | None = None


@dataclass
class AdminCommand:
    command_id: str
    command_type: str
    idempotency_key: str
    target_draft_id: str | None = None
    requested_by: str | None = None
    payload: dict = field(default_factory=dict)
    status: str = "pending"
    correlation_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: str | None = None
    processed_at: str | None = None
