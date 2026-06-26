"""review_workflow モジュールのユニットテスト（TDD: RED→GREEN）。

正本: openspec/changes/issue-19-implement-review-approval-workflow/specs/review-workflow/spec.md
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from spautopost.errors import InvalidTransitionError, PublishGateError
from spautopost.review_workflow import VALID_TRANSITIONS, apply_review_action, assert_publishable
from spautopost.storage.models import DraftStatus, ReviewAction

# --- fixtures ---

NOW = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
_counter = 0


def _id_factory() -> str:
    global _counter
    _counter += 1
    return f"id-{_counter:04d}"


# --- VALID_TRANSITIONS の構造チェック ---


class TestValidTransitions:
    def test_covers_all_expected_paths(self) -> None:
        """D3 の遷移テーブルを網羅している。"""
        expected: set[tuple[str, str]] = {
            ("created", "request_review"),
            ("generated", "request_review"),
            ("regeneration_requested", "request_review"),
            ("review_requested", "comment"),
            ("review_requested", "approve"),
            ("review_requested", "reject"),
            ("review_requested", "request_regeneration"),
            ("reviewed", "approve"),
            ("reviewed", "reject"),
            ("reviewed", "request_regeneration"),
        }
        actual = set(VALID_TRANSITIONS.keys())
        assert actual == expected

    def test_all_targets_are_valid_draft_statuses(self) -> None:
        from spautopost.storage.models import DRAFT_STATUSES

        for (_, _action), target in VALID_TRANSITIONS.items():
            assert target in DRAFT_STATUSES, f"{target!r} is not a valid DraftStatus"


# --- apply_review_action: 有効遷移 ---


class TestApplyReviewActionValidTransitions:
    @pytest.mark.parametrize(
        "from_status, action, expected_next",
        [
            ("created", "request_review", "review_requested"),
            ("generated", "request_review", "review_requested"),
            ("regeneration_requested", "request_review", "review_requested"),
            ("review_requested", "comment", "reviewed"),
            ("review_requested", "approve", "approved"),
            ("review_requested", "reject", "rejected"),
            ("review_requested", "request_regeneration", "regeneration_requested"),
            ("reviewed", "approve", "approved"),
            ("reviewed", "reject", "rejected"),
            ("reviewed", "request_regeneration", "regeneration_requested"),
        ],
    )
    def test_valid_transition_returns_next_status(
        self,
        from_status: DraftStatus,
        action: ReviewAction,
        expected_next: DraftStatus,
    ) -> None:
        next_status, event = apply_review_action(
            draft_id="d-001",
            current_status=from_status,
            action=action,
            reviewer="alice",
            comment=None,
            now=NOW,
            id_factory=_id_factory,
        )
        assert next_status == expected_next

    def test_review_event_has_correct_fields(self) -> None:
        next_status, event = apply_review_action(
            draft_id="d-002",
            current_status="review_requested",
            action="approve",
            reviewer="bob",
            comment="LGTM",
            now=NOW,
            id_factory=_id_factory,
        )
        assert event.draft_id == "d-002"
        assert event.reviewer == "bob"
        assert event.action == "approve"
        assert event.previous_status == "review_requested"
        assert event.next_status == "approved"
        assert event.comment == "LGTM"
        assert event.created_at == NOW

    def test_review_event_without_comment(self) -> None:
        _next, event = apply_review_action(
            draft_id="d-003",
            current_status="generated",
            action="request_review",
            reviewer="carol",
            comment=None,
            now=NOW,
            id_factory=_id_factory,
        )
        assert event.comment is None

    def test_regeneration_request(self) -> None:
        next_status, event = apply_review_action(
            draft_id="d-004",
            current_status="review_requested",
            action="request_regeneration",
            reviewer="dave",
            comment="needs rework",
            now=NOW,
            id_factory=_id_factory,
        )
        assert next_status == "regeneration_requested"
        assert event.next_status == "regeneration_requested"

    def test_regeneration_requested_can_be_reviewed_again(self) -> None:
        next_status, _event = apply_review_action(
            draft_id="d-005",
            current_status="regeneration_requested",
            action="request_review",
            reviewer="eve",
            comment=None,
            now=NOW,
            id_factory=_id_factory,
        )
        assert next_status == "review_requested"


# --- apply_review_action: 不正遷移 ---


class TestApplyReviewActionInvalidTransitions:
    @pytest.mark.parametrize(
        "from_status, action",
        [
            ("approved", "request_review"),
            ("approved", "approve"),
            ("rejected", "approve"),
            ("published", "request_review"),
            ("published", "approve"),
            ("publishing", "approve"),
            ("failed", "approve"),
            ("cancelled", "approve"),
            ("created", "approve"),
            ("generated", "reject"),
        ],
    )
    def test_invalid_transition_raises(
        self, from_status: DraftStatus, action: ReviewAction
    ) -> None:
        with pytest.raises(InvalidTransitionError) as exc_info:
            apply_review_action(
                draft_id="d-bad",
                current_status=from_status,
                action=action,
                reviewer="mallory",
                comment=None,
                now=NOW,
                id_factory=_id_factory,
            )
        err = exc_info.value
        assert err.previous_status == from_status
        assert err.action == action

    def test_error_contains_attempted_status(self) -> None:
        with pytest.raises(InvalidTransitionError) as exc_info:
            apply_review_action(
                draft_id="d-bad2",
                current_status="approved",
                action="approve",
                reviewer="mallory",
                comment=None,
                now=NOW,
                id_factory=_id_factory,
            )
        # attempted_status は "approved" のまま（再承認不可）
        assert "approved" in str(exc_info.value)


# --- assert_publishable ---


class TestAssertPublishable:
    def test_approved_draft_passes_gate(self) -> None:
        assert_publishable(draft_id="d-ok", draft_status="approved")  # no raise

    @pytest.mark.parametrize(
        "status",
        [
            "created",
            "generated",
            "review_requested",
            "reviewed",
            "rejected",
            "regeneration_requested",
            "publishing",
            "published",
            "failed",
            "cancelled",
        ],
    )
    def test_non_approved_draft_raises_publish_gate_error(self, status: DraftStatus) -> None:
        with pytest.raises(PublishGateError) as exc_info:
            assert_publishable(draft_id="d-fail", draft_status=status)
        err = exc_info.value
        assert err.draft_id == "d-fail"
        assert err.actual_status == status

    def test_error_message_contains_draft_id_and_status(self) -> None:
        with pytest.raises(PublishGateError) as exc_info:
            assert_publishable(draft_id="draft-xyz", draft_status="generated")
        msg = str(exc_info.value)
        assert "draft-xyz" in msg
        assert "generated" in msg
