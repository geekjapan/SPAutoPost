"""publish_site_page オーケストレーションの単体テスト（fake 注入・network 非依存）。"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

import pytest

from spautopost.errors import PublishGateError
from spautopost.graph.errors import GraphApiError, GraphAuthError
from spautopost.graph.publisher import build_idempotency_key, publish_site_page
from spautopost.llm import ProviderMetadata
from spautopost.storage.port import StoragePort

from .conftest import NOW, SECRET_TOKEN, FakePagesClient, FakeTokenProvider

_COUNTER = {"n": 0}


def _ids() -> str:
    _COUNTER["n"] += 1
    return f"id-{_COUNTER['n']:04d}"


def _common(payload: dict[str, Any], metadata: ProviderMetadata) -> dict[str, Any]:
    return dict(
        draft_id="draft-1",
        draft_status="approved",
        title="Example の脆弱性",
        target_site_id="site-1",
        target_page_library_id="lib-1",
        advisory_ids=["adv-1"],
        advisory_id="adv-1",
        provider=metadata,
        client_id="poc-client-id",
        now=NOW,
        id_factory=_ids,
    )


def test_dry_run_records_dry_run_publication_and_skips_graph(
    store: StoragePort, payload: dict[str, Any], metadata: ProviderMetadata
) -> None:
    token = FakeTokenProvider()
    client = FakePagesClient()

    result = publish_site_page(
        payload,
        dry_run=True,
        store=store,
        token_provider=token,
        client=client,
        **_common(payload, metadata),
    )

    assert token.calls == 0
    assert client.create_calls == []
    assert result.dry_run is True
    assert result.publication.publication_status == "dry_run"
    assert result.publication.operation == "dry-run"
    assert result.audit_events[0].event_type == "publish_dry_run"
    assert result.audit_events[0].result == "success"
    # 永続化されている。
    assert store.publications.get(result.publication.publication_id) is not None
    assert len(store.audit_events.list()) == 1


def test_live_success_records_published_with_actor(
    store: StoragePort, payload: dict[str, Any], metadata: ProviderMetadata
) -> None:
    token = FakeTokenProvider()
    client = FakePagesClient(page_id="page-xyz")

    result = publish_site_page(
        payload,
        dry_run=False,
        store=store,
        token_provider=token,
        client=client,
        **_common(payload, metadata),
    )

    assert token.calls == 1
    assert len(client.create_calls) == 1
    # request_body が title を含む（build_create_page_request 経由）。
    assert client.create_calls[0]["request_body"]["title"] == "Example の脆弱性"
    assert result.created is True
    assert result.publication.publication_status == "published"
    assert result.publication.sharepoint_page_id == "page-xyz"
    assert result.publication.operation == "create"
    create_audit = result.audit_events[0]
    assert create_audit.event_type == "publish_create"
    assert create_audit.actor == "poc.user@example.com"
    assert create_audit.service_principal == "poc-client-id"


def test_live_does_not_leak_token_into_records(
    store: StoragePort, payload: dict[str, Any], metadata: ProviderMetadata
) -> None:
    token = FakeTokenProvider()
    client = FakePagesClient()

    result = publish_site_page(
        payload,
        dry_run=False,
        store=store,
        token_provider=token,
        client=client,
        **_common(payload, metadata),
    )

    # 永続化される Publication・AuditEvent にトークンが漏れていないことを確認する。
    # FakePagesClient.create_calls は API 呼び出しの引数を記録する test double なので対象外。
    serialized = json.dumps(
        {
            "publication": asdict(result.publication),
            "audit": [asdict(event) for event in result.audit_events],
        },
        default=str,
        ensure_ascii=False,
    )
    assert SECRET_TOKEN not in serialized


def test_live_promote_publishes_and_records_result(
    store: StoragePort, payload: dict[str, Any], metadata: ProviderMetadata
) -> None:
    token = FakeTokenProvider()
    client = FakePagesClient(page_id="page-1")

    result = publish_site_page(
        payload,
        dry_run=False,
        store=store,
        token_provider=token,
        client=client,
        promote=True,
        **_common(payload, metadata),
    )

    assert len(client.publish_calls) == 1
    assert client.publish_calls[0]["page_id"] == "page-1"
    assert result.publication.operation == "publish"
    event_types = [event.event_type for event in result.audit_events]
    assert event_types == ["publish_create", "publish_result"]


def test_live_failure_records_failed_and_does_not_raise(
    store: StoragePort, payload: dict[str, Any], metadata: ProviderMetadata
) -> None:
    token = FakeTokenProvider()
    client = FakePagesClient(create_error=GraphApiError("denied", status_code=403))

    result = publish_site_page(
        payload,
        dry_run=False,
        store=store,
        token_provider=token,
        client=client,
        **_common(payload, metadata),
    )

    assert result.created is False
    assert result.publication.publication_status == "failed"
    assert result.publication.error_code == "authorization_failed"
    assert result.publication.retryable is False
    assert result.audit_events[0].event_type == "error"
    assert result.audit_events[0].result == "failure"


def test_live_rate_limited_is_retryable(
    store: StoragePort, payload: dict[str, Any], metadata: ProviderMetadata
) -> None:
    token = FakeTokenProvider()
    client = FakePagesClient(create_error=GraphApiError("slow down", status_code=429))

    result = publish_site_page(
        payload,
        dry_run=False,
        store=store,
        token_provider=token,
        client=client,
        **_common(payload, metadata),
    )

    assert result.publication.error_code == "graph_rate_limited"
    assert result.publication.retryable is True


def test_live_auth_failure_records_authentication_failed(
    store: StoragePort, payload: dict[str, Any], metadata: ProviderMetadata
) -> None:
    token = FakeTokenProvider(error=GraphAuthError("no sign-in"))
    client = FakePagesClient()

    result = publish_site_page(
        payload,
        dry_run=False,
        store=store,
        token_provider=token,
        client=client,
        **_common(payload, metadata),
    )

    assert client.create_calls == []
    assert result.publication.publication_status == "failed"
    assert result.publication.error_code == "authentication_failed"
    assert result.publication.retryable is False


def test_live_server_error_maps_to_graph_api_error(
    store: StoragePort, payload: dict[str, Any], metadata: ProviderMetadata
) -> None:
    client = FakePagesClient(create_error=GraphApiError("boom", status_code=500, retryable=True))

    result = publish_site_page(
        payload,
        dry_run=False,
        store=store,
        token_provider=FakeTokenProvider(),
        client=client,
        **_common(payload, metadata),
    )

    assert result.publication.error_code == "graph_api_error"
    assert result.publication.retryable is True


def test_live_unexpected_error_maps_to_publish_failed(
    store: StoragePort, payload: dict[str, Any], metadata: ProviderMetadata
) -> None:
    client = FakePagesClient(create_error=ValueError("unexpected"))

    result = publish_site_page(
        payload,
        dry_run=False,
        store=store,
        token_provider=FakeTokenProvider(),
        client=client,
        **_common(payload, metadata),
    )

    assert result.publication.publication_status == "failed"
    assert result.publication.error_code == "publish_failed"
    assert result.publication.retryable is False


def test_idempotency_skip_when_already_published(
    store: StoragePort, payload: dict[str, Any], metadata: ProviderMetadata
) -> None:
    first_client = FakePagesClient(page_id="page-1")
    publish_site_page(
        payload,
        dry_run=False,
        store=store,
        token_provider=FakeTokenProvider(),
        client=first_client,
        **_common(payload, metadata),
    )

    # 同一 draft / 投稿先で再実行 → 新規 Graph 作成しない。
    second_client = FakePagesClient(page_id="page-2")
    second_token = FakeTokenProvider()
    result = publish_site_page(
        payload,
        dry_run=False,
        store=store,
        token_provider=second_token,
        client=second_client,
        **_common(payload, metadata),
    )

    assert result.created is False
    assert second_token.calls == 0
    assert second_client.create_calls == []
    assert result.publication.sharepoint_page_id == "page-1"


def test_live_requires_token_and_client(
    store: StoragePort, payload: dict[str, Any], metadata: ProviderMetadata
) -> None:
    try:
        publish_site_page(
            payload,
            dry_run=False,
            store=store,
            token_provider=None,
            client=None,
            **_common(payload, metadata),
        )
    except GraphAuthError:
        return
    raise AssertionError("expected GraphAuthError when live publish lacks token/client")


def test_idempotency_key_deterministic_and_target_sensitive() -> None:
    base = dict(
        draft_id="d1",
        target_site_id="site-1",
        target_page_library_id="lib-1",
        advisory_ids=["adv-2", "adv-1"],
        title="  Example   Vulnerability ",
    )
    key_a = build_idempotency_key(**base)
    # 大文字小文字・空白・advisory 順の違いは同一キー。
    key_b = build_idempotency_key(
        draft_id="d1",
        target_site_id="site-1",
        target_page_library_id="lib-1",
        advisory_ids=["adv-1", "adv-2"],
        title="example vulnerability",
    )
    assert key_a == key_b
    # 投稿先が違えば別キー。
    key_other_site = build_idempotency_key(**{**base, "target_site_id": "site-2"})
    assert key_other_site != key_a


# --- publish gate tests ---


class TestPublishGate:
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
    def test_non_approved_draft_raises_before_any_storage_write(
        self, store: StoragePort, payload: dict[str, Any], metadata: ProviderMetadata, status: str
    ) -> None:
        client = FakePagesClient()
        token = FakeTokenProvider()
        with pytest.raises(PublishGateError) as exc_info:
            publish_site_page(
                payload,
                dry_run=False,
                store=store,
                token_provider=token,
                client=client,
                draft_id="draft-1",
                draft_status=status,  # type: ignore[arg-type]
                title="Test",
                target_site_id="site-1",
                target_page_library_id="lib-1",
                advisory_ids=[],
                advisory_id=None,
                provider=metadata,
                client_id="poc-client-id",
                now=NOW,
                id_factory=_ids,
            )
        assert exc_info.value.actual_status == status
        # Storage には何も書かれていない。
        assert store.publications.list() == []
        assert store.audit_events.list() == []
        assert client.create_calls == []
        assert token.calls == 0

    def test_dry_run_non_approved_also_raises(
        self, store: StoragePort, payload: dict[str, Any], metadata: ProviderMetadata
    ) -> None:
        with pytest.raises(PublishGateError):
            publish_site_page(
                payload,
                dry_run=True,
                store=store,
                draft_id="draft-1",
                draft_status="review_requested",
                title="Test",
                target_site_id="site-1",
                target_page_library_id="lib-1",
                advisory_ids=[],
                advisory_id=None,
                provider=metadata,
                client_id="poc-client-id",
                now=NOW,
                id_factory=_ids,
            )

    def test_approved_live_passes_gate(
        self, store: StoragePort, payload: dict[str, Any], metadata: ProviderMetadata
    ) -> None:
        result = publish_site_page(
            payload,
            dry_run=False,
            store=store,
            token_provider=FakeTokenProvider(),
            client=FakePagesClient(),
            **_common(payload, metadata),  # draft_status="approved"
        )
        assert result.publication.publication_status == "published"
