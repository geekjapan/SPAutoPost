"""DTO（models.py）の境界・不変・型値テスト（backend 不要）。"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta, timezone

import pytest

from spautopost.storage.errors import ConstraintViolationError
from spautopost.storage.models import (
    AUDIT_EVENT_TYPES,
    AuditEvent,
    Publication,
    SourceRecord,
    ensure_utc,
)

from .contract_factories import make_audit_event, make_publication, make_source_record


def test_dto_is_frozen() -> None:
    record = make_source_record()
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.source_name = "changed"  # type: ignore[misc]


def test_naive_datetime_rejected_at_boundary() -> None:
    with pytest.raises(ConstraintViolationError):
        SourceRecord(
            source_record_id="x",
            source_type="manual",
            source_name="n",
            retrieved_at=datetime(2024, 1, 1),  # naive
            raw_hash="h",
            parser_version="p",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )


def test_non_utc_tz_normalized_to_utc() -> None:
    jst = timezone(timedelta(hours=9))
    record = make_source_record()
    converted = ensure_utc(datetime(2024, 1, 1, 9, 0, 0, tzinfo=jst), "x")
    assert converted == datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    assert record.created_at.utcoffset() == timedelta(0)


def test_idempotency_key_required_non_blank() -> None:
    with pytest.raises(ConstraintViolationError):
        make_publication(idempotency_key="")
    with pytest.raises(ConstraintViolationError):
        make_publication(idempotency_key="   ")


def test_idempotency_key_valid() -> None:
    pub = make_publication(idempotency_key="ok-key")
    assert isinstance(pub, Publication)
    assert pub.idempotency_key == "ok-key"


def test_audit_event_type_has_15_values() -> None:
    assert len(AUDIT_EVENT_TYPES) == 15


def test_invalid_audit_event_type_rejected() -> None:
    with pytest.raises(ConstraintViolationError):
        AuditEvent(
            audit_event_id="a",
            event_type="not_a_type",  # type: ignore[arg-type]
            correlation_id="c",
            result="success",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )


def test_valid_audit_event() -> None:
    event = make_audit_event()
    assert isinstance(event, AuditEvent)
    assert event.event_type in AUDIT_EVENT_TYPES
