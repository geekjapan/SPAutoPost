"""contract suite が用いる DTO ビルダ（決定論的・tz-aware UTC）。

各 backend を横断する共有テストデータ。timestamp は全て tz-aware UTC。
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from spautopost.storage.models import (
    AdminCommand,
    Advisory,
    AuditEvent,
    DraftPost,
    Publication,
    ReviewEvent,
    SourceRecord,
)


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=UTC)


def make_source_record(
    *, source_record_id: str = "src-1", created_at: datetime | None = None
) -> SourceRecord:
    return SourceRecord(
        source_record_id=source_record_id,
        source_type="nvd",
        source_name="NVD",
        retrieved_at=_utc(2024, 1, 1),
        raw_hash="hash-1",
        parser_version="p1",
        created_at=created_at or _utc(2024, 1, 1),
        source_url="https://example.test/a",
        http_status=200,
        etag="etag-1",
        last_modified="Mon, 01 Jan 2024 00:00:00 GMT",
    )


def make_advisory(*, advisory_id: str = "adv-1", created_at: datetime | None = None) -> Advisory:
    return Advisory(
        advisory_id=advisory_id,
        title="Example advisory",
        summary="An example summary.",
        created_at=created_at or _utc(2024, 1, 1),
        normalized_at=_utc(2024, 1, 1),
        published_at=_utc(2023, 12, 31),
        updated_at=_utc(2024, 1, 2),
        severity="high",
        cve_ids=["CVE-2024-0001"],
        vendor_advisory_ids=["VEND-1", "VEND-2"],
        cvss_score=7.5,
    )


def make_draft_post(
    *,
    draft_id: str = "draft-1",
    created_at: datetime | None = None,
    advisory_id: str | None = None,
) -> DraftPost:
    return DraftPost(
        draft_id=draft_id,
        title="Draft title",
        audience="general_users",
        urgency="high",
        summary_for_users="What users need to know.",
        impact="The impact statement.",
        status="created",
        created_at=created_at or _utc(2024, 1, 1),
        updated_at=_utc(2024, 1, 1),
        advisory_id=advisory_id,
        advisory_ids=["adv-1"],
        required_actions=["Apply patch"],
    )


def make_review_event(
    *, review_event_id: str = "rev-1", created_at: datetime | None = None
) -> ReviewEvent:
    return ReviewEvent(
        review_event_id=review_event_id,
        draft_id="draft-1",
        reviewer="alice",
        action="approve",
        created_at=created_at or _utc(2024, 1, 1),
        comment="Looks good.",
    )


def make_publication(
    *,
    publication_id: str = "pub-1",
    idempotency_key: str = "idem-1",
    created_at: datetime | None = None,
) -> Publication:
    return Publication(
        publication_id=publication_id,
        draft_id="draft-1",
        target_type="site-page",
        target_site_id="site-1",
        publication_status="pending",
        idempotency_key=idempotency_key,
        created_at=created_at or _utc(2024, 1, 1),
        updated_at=_utc(2024, 1, 1),
        operation="dry-run",
    )


def make_audit_event(
    *, audit_event_id: str = "aud-1", created_at: datetime | None = None
) -> AuditEvent:
    return AuditEvent(
        audit_event_id=audit_event_id,
        event_type="publish_dry_run",
        correlation_id="corr-1",
        result="success",
        created_at=created_at or _utc(2024, 1, 1),
        target_site_id="site-1",
        idempotency_key="idem-1",
        operation="dry-run",
    )


def make_admin_command(
    *,
    command_id: str = "cmd-1",
    idempotency_key: str = "cmd-idem-1",
    created_at: datetime | None = None,
    target_draft_id: str | None = "draft-1",
    status: str = "pending",
    payload: dict[str, Any] | None = None,
) -> AdminCommand:
    return AdminCommand(
        command_id=command_id,
        command_type="approve",
        target_draft_id=target_draft_id,
        requested_by="alice",
        payload=payload or {"comment": "ok"},
        idempotency_key=idempotency_key,
        status=status,  # type: ignore[arg-type]
        correlation_id="corr-1",
        created_at=created_at or _utc(2024, 1, 1),
    )
