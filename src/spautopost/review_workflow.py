"""DraftPost のレビュー・承認ワークフロー。

正本: openspec/changes/issue-19-implement-review-approval-workflow/specs/review-workflow/spec.md

純粋関数のみ（StoragePort への依存なし）。呼び出し側が ReviewEvent を StoragePort に append する。
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime

from .errors import InvalidTransitionError, PublishGateError
from .storage.models import DraftStatus, ReviewAction, ReviewEvent

IdFactory = Callable[[], str]

# 許可される (current_status, action) → next_status のテーブル。
# D3 設計判断の正本。
VALID_TRANSITIONS: dict[tuple[DraftStatus, ReviewAction], DraftStatus] = {
    ("created", "request_review"): "review_requested",
    ("generated", "request_review"): "review_requested",
    ("regeneration_requested", "request_review"): "review_requested",
    ("review_requested", "comment"): "reviewed",
    ("review_requested", "approve"): "approved",
    ("review_requested", "reject"): "rejected",
    ("review_requested", "request_regeneration"): "regeneration_requested",
    ("reviewed", "approve"): "approved",
    ("reviewed", "reject"): "rejected",
    ("reviewed", "request_regeneration"): "regeneration_requested",
}


def _default_id_factory() -> str:
    return uuid.uuid4().hex


def apply_review_action(
    *,
    draft_id: str,
    current_status: DraftStatus,
    action: ReviewAction,
    reviewer: str,
    comment: str | None,
    now: datetime,
    id_factory: IdFactory = _default_id_factory,
) -> tuple[DraftStatus, ReviewEvent]:
    """レビューアクションを適用し (next_status, ReviewEvent) を返す。

    合法的な遷移のみ受理し、不正な遷移は InvalidTransitionError を送出する。
    副作用なし（StoragePort への書き込みは呼び出し側の責務）。
    """
    next_status = VALID_TRANSITIONS.get((current_status, action))
    if next_status is None:
        # 想定される next_status を "unknown" として InvalidTransitionError に渡す
        raise InvalidTransitionError(
            previous_status=current_status,
            action=action,
            attempted_status="<not allowed>",
        )

    event = ReviewEvent(
        review_event_id=id_factory(),
        draft_id=draft_id,
        reviewer=reviewer,
        action=action,
        created_at=now,
        comment=comment,
        previous_status=current_status,
        next_status=next_status,
    )
    return next_status, event


def assert_publishable(*, draft_id: str, draft_status: DraftStatus) -> None:
    """draft_status が 'approved' でなければ PublishGateError を送出する。

    publish_site_page() の先頭で呼ぶ（dry_run を問わず）。
    """
    if draft_status != "approved":
        raise PublishGateError(draft_id=draft_id, actual_status=draft_status)
