"""dry-run preview / 監査イベント組み立ての単体テスト。"""

from __future__ import annotations

from datetime import UTC, datetime

from spautopost.dry_run import (
    DEADLINE_UNSET,
    REQUIRED_SECTION_HEADINGS,
    TARGET_SECTION_PLACEHOLDER,
    audit_event_to_dict,
    build_error_audit_event,
    build_preview_audit_event,
    build_site_page_payload,
)
from spautopost.llm import DraftOutput, ProviderMetadata

NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=UTC)

DRAFT = DraftOutput(
    title="[重要] Example の脆弱性対応について",
    summary_for_users="概要本文。",
    impact="影響本文。",
    required_actions=("更新してください。",),
    admin_actions=("適用状況を確認してください。",),
    references=({"label": "Vendor", "url": "https://example.com/a", "type": "vendor"},),
    warnings=("test_mock generated.",),
    uncertainty_notes=("対象製品が不明。",),
    generation_input_hash="abc123",
)

META = ProviderMetadata(
    provider_name="test_mock",
    provider_type="test_mock",
    model=None,
    prompt_version="v1",
)


def test_payload_has_required_sections_in_order() -> None:
    # Act
    payload = build_site_page_payload(
        DRAFT, urgency="high", target_site_id="env:SITE", target_page_library_id="env:LIB"
    )

    # Assert
    headings = [section["heading"] for section in payload["sections"]]
    assert tuple(headings) == REQUIRED_SECTION_HEADINGS
    assert payload["title"] == DRAFT.title
    assert payload["mode"] == "site-page"
    assert payload["urgency"] == "high"


def test_payload_maps_draft_fields() -> None:
    payload = build_site_page_payload(
        DRAFT, urgency="normal", target_site_id=None, target_page_library_id=None
    )
    by_heading = {s["heading"]: s for s in payload["sections"]}

    assert by_heading["概要"]["body"] == "概要本文。"
    assert by_heading["影響"]["body"] == "影響本文。"
    assert by_heading["対象"]["body"] == TARGET_SECTION_PLACEHOLDER
    assert by_heading["利用者が行う対応"]["items"] == ["更新してください。"]
    assert by_heading["管理者が行う対応"]["items"] == ["適用状況を確認してください。"]
    # deadline 未設定なら placeholder
    assert by_heading["対応期限または推奨対応時期"]["body"] == DEADLINE_UNSET
    assert by_heading["参考情報"]["references"][0]["url"] == "https://example.com/a"
    assert payload["review_warnings"] == ["test_mock generated.", "対象製品が不明。"]


def test_preview_audit_event_records_minimal_provenance() -> None:
    # Act
    event = build_preview_audit_event(
        provider=META,
        draft=DRAFT,
        correlation_id="corr-1",
        audit_event_id="evt-1",
        now=NOW,
        advisory_id="ADV-1",
        target_site_id="env:SITE",
        target_page_library_id="env:LIB",
    )

    # Assert
    assert event.event_type == "publish_dry_run"
    assert event.result == "success"
    assert event.operation == "dry-run"
    assert event.provider_name == "test_mock"
    assert event.provider_type == "test_mock"
    assert event.prompt_version == "v1"
    assert event.related_ids == {"advisory_id": "ADV-1", "generation_input_hash": "abc123"}


def test_error_audit_event_tracks_failure() -> None:
    event = build_error_audit_event(
        correlation_id="corr-1",
        audit_event_id="evt-err",
        now=NOW,
        error_code="draft_generation_failed",
        error_message="provider boom",
        provider=META,
    )

    assert event.event_type == "error"
    assert event.result == "failure"
    assert event.error_code == "draft_generation_failed"
    assert event.error_message == "provider boom"
    assert event.provider_name == "test_mock"


def test_audit_event_to_dict_drops_none_and_isoformats_datetime() -> None:
    event = build_preview_audit_event(
        provider=META,
        draft=DRAFT,
        correlation_id="corr-1",
        audit_event_id="evt-1",
        now=NOW,
    )

    as_dict = audit_event_to_dict(event)

    assert as_dict["created_at"] == "2026-06-24T12:00:00+00:00"
    assert as_dict["event_type"] == "publish_dry_run"
    # None フィールド（actor 等）は省かれる
    assert "actor" not in as_dict
    assert "error_code" not in as_dict
