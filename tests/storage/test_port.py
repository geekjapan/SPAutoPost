"""port.py の構造テスト（Protocol の形、backend 不要）。"""

from __future__ import annotations

from spautopost.storage.port import (
    AdminCommandRepository,
    AuditEventRepository,
    PublicationRepository,
    ReviewEventRepository,
    SourceRecordRepository,
)


def test_append_only_repos_have_no_upsert() -> None:
    assert hasattr(ReviewEventRepository, "append")
    assert hasattr(AuditEventRepository, "append")
    assert not hasattr(ReviewEventRepository, "upsert")
    assert not hasattr(AuditEventRepository, "upsert")


def test_mutable_repo_exposes_upsert() -> None:
    assert hasattr(SourceRecordRepository, "upsert")


def test_publication_repo_idempotency_surface() -> None:
    assert hasattr(PublicationRepository, "create_if_absent")
    assert hasattr(PublicationRepository, "get_by_idempotency_key")


def test_admin_command_repo_queue_surface() -> None:
    assert hasattr(AdminCommandRepository, "append")
    assert hasattr(AdminCommandRepository, "claim_pending")
    assert hasattr(AdminCommandRepository, "complete")
    assert hasattr(AdminCommandRepository, "fail")
