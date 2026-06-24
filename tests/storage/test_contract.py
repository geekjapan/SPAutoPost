"""backend 横断の共有 contract suite。

``storage`` フィクスチャ（tests/storage/conftest.py）にパラメタライズされる。
backend が 1 つも登録されていない TASK BLOCK 1 時点では、各テストは収集されるが
パラメータ無しのため実行されない（=未提供 / RED 状態）。backend を
``BACKEND_SPECS`` に追記すると同一テストが PG / SQLite 双方で実行される。

網羅: get / list（決定論順 + limit/offset）/ upsert / append-only /
create_if_absent / idempotency / timestamp 往復。
"""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING

import pytest

from spautopost.storage.errors import ConstraintViolationError

from .contract_factories import (
    make_admin_command,
    make_advisory,
    make_audit_event,
    make_draft_post,
    make_publication,
    make_review_event,
    make_source_record,
)

if TYPE_CHECKING:
    from spautopost.storage.port import StoragePort


# --- get / upsert ----------------------------------------------------------


def test_get_missing_returns_none(storage: StoragePort) -> None:
    assert storage.source_records.get("does-not-exist") is None


def test_upsert_then_get_roundtrips(storage: StoragePort) -> None:
    record = make_source_record()
    storage.source_records.upsert(record)
    fetched = storage.source_records.get(record.source_record_id)
    assert fetched == record


def test_upsert_is_idempotent_update(storage: StoragePort) -> None:
    storage.advisories.upsert(make_advisory(advisory_id="adv-1"))
    updated = make_advisory(advisory_id="adv-1")
    storage.advisories.upsert(updated)
    rows = storage.advisories.list()
    assert len([r for r in rows if r.advisory_id == "adv-1"]) == 1


# --- list: 決定論順 + ページング -------------------------------------------


def test_list_deterministic_order(storage: StoragePort) -> None:
    from datetime import datetime

    early = datetime(2024, 1, 1, tzinfo=UTC)
    late = datetime(2024, 1, 2, tzinfo=UTC)
    storage.source_records.upsert(make_source_record(source_record_id="b", created_at=late))
    storage.source_records.upsert(make_source_record(source_record_id="a", created_at=early))
    storage.source_records.upsert(make_source_record(source_record_id="a2", created_at=early))
    ids = [r.source_record_id for r in storage.source_records.list()]
    # created_at ASC, 主キー ASC: early(a, a2) -> late(b)
    assert ids == ["a", "a2", "b"]


def test_list_limit_offset(storage: StoragePort) -> None:
    for i in range(5):
        storage.advisories.upsert(make_advisory(advisory_id=f"adv-{i}"))
    page = storage.advisories.list(limit=2, offset=1)
    assert len(page) == 2


# --- append-only (ReviewEvent / AuditEvent) --------------------------------


def test_review_event_append_only(storage: StoragePort) -> None:
    storage.draft_posts.upsert(make_draft_post(draft_id="draft-1"))
    event = make_review_event(review_event_id="rev-1")
    storage.review_events.append(event)
    assert storage.review_events.get("rev-1") == event
    # append-only repository は upsert を露出しない。
    assert not hasattr(storage.review_events, "upsert")


def test_audit_event_append_and_get(storage: StoragePort) -> None:
    event = make_audit_event(audit_event_id="aud-1")
    storage.audit_events.append(event)
    assert storage.audit_events.get("aud-1") == event
    assert not hasattr(storage.audit_events, "upsert")


# --- idempotency / create_if_absent ----------------------------------------


def test_create_if_absent_first_then_existing(storage: StoragePort) -> None:
    storage.draft_posts.upsert(make_draft_post(draft_id="draft-1"))
    pub = make_publication(publication_id="pub-1", idempotency_key="idem-1")
    created_pub, created = storage.publications.create_if_absent(pub)
    assert created is True
    again = make_publication(publication_id="pub-2", idempotency_key="idem-1")
    existing_pub, created_again = storage.publications.create_if_absent(again)
    assert created_again is False
    assert existing_pub.idempotency_key == created_pub.idempotency_key


def test_duplicate_idempotency_key_rejected_on_upsert(storage: StoragePort) -> None:
    storage.draft_posts.upsert(make_draft_post(draft_id="draft-1"))
    storage.publications.upsert(make_publication(publication_id="pub-1", idempotency_key="k"))
    with pytest.raises(ConstraintViolationError):
        storage.publications.upsert(make_publication(publication_id="pub-2", idempotency_key="k"))


def test_get_by_idempotency_key(storage: StoragePort) -> None:
    storage.draft_posts.upsert(make_draft_post(draft_id="draft-1"))
    pub = make_publication(publication_id="pub-1", idempotency_key="idem-9")
    storage.publications.create_if_absent(pub)
    found = storage.publications.get_by_idempotency_key("idem-9")
    assert found is not None and found.publication_id == "pub-1"
    assert storage.publications.get_by_idempotency_key("missing") is None


# --- AdminCommand queue ----------------------------------------------------


def test_admin_command_claim_is_exclusive(storage: StoragePort) -> None:
    storage.draft_posts.upsert(make_draft_post(draft_id="draft-1"))
    for i in range(3):
        storage.admin_commands.append(
            make_admin_command(command_id=f"cmd-{i}", idempotency_key=f"cmd-idem-{i}")
        )

    first = storage.admin_commands.claim_pending(limit=2)
    second = storage.admin_commands.claim_pending(limit=2)

    first_ids = {command.command_id for command in first}
    second_ids = {command.command_id for command in second}
    assert first_ids.isdisjoint(second_ids)
    assert len(first_ids) == 2
    assert len(second_ids) == 1
    assert all(command.status == "processing" for command in [*first, *second])


def test_admin_command_complete_and_fail(storage: StoragePort) -> None:
    storage.draft_posts.upsert(make_draft_post(draft_id="draft-1"))
    storage.admin_commands.append(make_admin_command(command_id="cmd-ok", idempotency_key="ok"))
    storage.admin_commands.append(make_admin_command(command_id="cmd-fail", idempotency_key="fail"))

    storage.admin_commands.complete("cmd-ok")
    storage.admin_commands.fail("cmd-fail", error_code="E_BOOM", error_message="exploded")

    completed = storage.admin_commands.get("cmd-ok")
    failed = storage.admin_commands.get("cmd-fail")
    assert completed is not None
    assert completed.status == "succeeded"
    assert completed.processed_at is not None
    assert failed is not None
    assert failed.status == "failed"
    assert failed.error_code == "E_BOOM"
    assert failed.error_message == "exploded"
    assert failed.processed_at is not None


def test_admin_command_duplicate_idempotency_rejected(storage: StoragePort) -> None:
    storage.draft_posts.upsert(make_draft_post(draft_id="draft-1"))
    storage.admin_commands.append(make_admin_command(command_id="cmd-1", idempotency_key="same"))
    with pytest.raises(ConstraintViolationError):
        storage.admin_commands.append(
            make_admin_command(command_id="cmd-2", idempotency_key="same")
        )


def test_publication_and_admin_command_idempotency_scopes_are_independent(
    storage: StoragePort,
) -> None:
    storage.draft_posts.upsert(make_draft_post(draft_id="draft-1"))
    storage.publications.upsert(make_publication(publication_id="pub-1", idempotency_key="shared"))
    storage.admin_commands.append(make_admin_command(command_id="cmd-1", idempotency_key="shared"))

    assert storage.publications.get_by_idempotency_key("shared") is not None
    assert storage.admin_commands.get("cmd-1") is not None


def test_admin_command_payload_rejects_secret_keys(storage: StoragePort) -> None:
    storage.draft_posts.upsert(make_draft_post(draft_id="draft-1"))

    with pytest.raises(ConstraintViolationError, match="payload"):
        storage.admin_commands.append(
            make_admin_command(
                command_id="cmd-secret",
                idempotency_key="secret",
                payload={"access_token": "secret-token"},
            )
        )


# --- timestamp 往復 --------------------------------------------------------


def test_timestamp_roundtrip_is_utc(storage: StoragePort) -> None:
    record = make_source_record()
    storage.source_records.upsert(record)
    fetched = storage.source_records.get(record.source_record_id)
    assert fetched is not None
    assert fetched.retrieved_at == record.retrieved_at
    assert fetched.retrieved_at.utcoffset() is not None


# --- transaction(): 複数操作の原子性 ---------------------------------------


def test_transaction_commits_multiple_operations(storage: StoragePort) -> None:
    """``transaction()`` 内の複数書き込みがまとめて commit される。"""
    with storage.transaction():
        storage.source_records.upsert(make_source_record(source_record_id="src-tx-1"))
        storage.advisories.upsert(make_advisory(advisory_id="adv-tx-1"))
    assert storage.source_records.get("src-tx-1") is not None
    assert storage.advisories.get("adv-tx-1") is not None


def test_transaction_rolls_back_whole_unit_on_failure(storage: StoragePort) -> None:
    """ブロック途中で失敗すると、先行する書き込みも含めて作業単位全体が rollback される。

    個別操作の commit を抑止していなければ、最初の upsert は残ってしまう（=回帰）。
    ここでは 2 件目で FK 違反（存在しない advisory_id を draft_posts が参照）を起こす。
    """
    with pytest.raises(ConstraintViolationError):
        with storage.transaction():
            storage.source_records.upsert(make_source_record(source_record_id="src-rollback"))
            storage.draft_posts.upsert(
                make_draft_post(draft_id="draft-rollback", advisory_id="nonexistent-advisory")
            )
    # 作業単位全体が巻き戻り、先行する source_records.upsert も残っていない。
    assert storage.source_records.get("src-rollback") is None
    assert storage.draft_posts.get("draft-rollback") is None
