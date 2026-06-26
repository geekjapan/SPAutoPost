"""Tests for spautopost.sharepoint_publisher (TDD).

カバレッジ対象:
- build_idempotency_key: 決定論・重複なし
- build_page_html: 必須セクション・HTML エスケープ
- publish_approved_draft:
    - status 検証（非 approved → PublishError）
    - dry-run（Graph 呼び出しなし・DraftPost 変更なし・Publication dry_run）
    - 実投稿成功（published + AuditEvent publish_result/success）
    - 冪等性（2 回目は既存 Publication を返す）
    - 投稿失敗（failed + AuditEvent publish_result/failure + PublishError）
- NoopGraphClient: ページ ID を返す
- MicrosoftGraphClient.from_env: token なしで GraphAuthError
- GraphAuthError: token 空で GraphAuthError
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from spautopost.errors import GraphAuthError, PublishError
from spautopost.sharepoint_publisher import (
    GraphPage,
    MicrosoftGraphClient,
    NoopGraphClient,
    build_idempotency_key,
    build_page_html,
    publish_approved_draft,
)
from spautopost.storage.models import DraftPost

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


def _make_draft(
    *,
    draft_id: str = "draft-36",
    status: str = "approved",
) -> DraftPost:
    return DraftPost(
        draft_id=draft_id,
        title="CVE-2024-9999 セキュリティ更新",
        audience="mixed",
        urgency="high",
        summary_for_users="影響を受けるシステムにパッチを適用してください。",
        impact="リモートコード実行の可能性があります。",
        status=status,  # type: ignore[arg-type]
        created_at=_utc(2024, 6, 1),
        updated_at=_utc(2024, 6, 1),
        advisory_ids=["adv-1", "adv-2"],
        required_actions=["パッチを適用する", "システムを再起動する"],
        admin_actions=["パッチ配布を確認する"],
        references=[{"label": "CVE-2024-9999", "url": "https://example.test/cve"}],
    )


def _build_sqlite_storage(tmp_path: Path) -> Any:
    from spautopost.config import StorageConfig
    from spautopost.storage.factory import build_storage

    port = build_storage(
        StorageConfig(
            provider="sqlite",
            database_url=None,
            sqlite_path=str(tmp_path / "test.sqlite3"),
        )
    )
    port.migrate()
    return port


# ---------------------------------------------------------------------------
# build_idempotency_key
# ---------------------------------------------------------------------------


def test_idempotency_key_deterministic() -> None:
    k1 = build_idempotency_key(
        draft_id="d1",
        target_site_id="s1",
        target_page_library_id="l1",
    )
    k2 = build_idempotency_key(
        draft_id="d1",
        target_site_id="s1",
        target_page_library_id="l1",
    )
    assert k1 == k2


def test_idempotency_key_differs_by_draft() -> None:
    k1 = build_idempotency_key(
        draft_id="d1",
        target_site_id="s1",
        target_page_library_id="l1",
    )
    k2 = build_idempotency_key(
        draft_id="d2",
        target_site_id="s1",
        target_page_library_id="l1",
    )
    assert k1 != k2


def test_idempotency_key_differs_by_site() -> None:
    k1 = build_idempotency_key(
        draft_id="d1",
        target_site_id="site-a",
        target_page_library_id="l1",
    )
    k2 = build_idempotency_key(
        draft_id="d1",
        target_site_id="site-b",
        target_page_library_id="l1",
    )
    assert k1 != k2


# ---------------------------------------------------------------------------
# build_page_html
# ---------------------------------------------------------------------------


def test_build_page_html_contains_summary() -> None:
    draft = _make_draft()
    html = build_page_html(draft)
    assert "概要" in html
    assert "パッチを適用してください" in html


def test_build_page_html_contains_impact() -> None:
    draft = _make_draft()
    html = build_page_html(draft)
    assert "影響" in html
    assert "リモートコード実行" in html


def test_build_page_html_contains_actions() -> None:
    draft = _make_draft()
    html = build_page_html(draft)
    assert "利用者が行う対応" in html
    assert "パッチを適用する" in html
    assert "管理者が行う対応" in html
    assert "パッチ配布を確認する" in html


def test_build_page_html_references() -> None:
    draft = _make_draft()
    html = build_page_html(draft)
    assert "参考情報" in html
    assert "CVE-2024-9999" in html
    assert "https://example.test/cve" in html


def test_build_page_html_escapes_special_chars() -> None:
    draft = dataclasses.replace(
        _make_draft(),
        summary_for_users='<script>alert("xss")</script>',
        impact="a & b > c",
    )
    html = build_page_html(draft)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&amp;" in html


# ---------------------------------------------------------------------------
# NoopGraphClient
# ---------------------------------------------------------------------------


def test_noop_graph_client_returns_page() -> None:
    client = NoopGraphClient()
    result = client.create_news_article(
        site_id="site-1",
        title="Test",
        html_content="<p>hello</p>",
    )
    assert isinstance(result, GraphPage)
    assert result.page_id  # non-empty


# ---------------------------------------------------------------------------
# MicrosoftGraphClient — auth
# ---------------------------------------------------------------------------


def test_microsoft_graph_client_from_env_missing_token() -> None:
    with pytest.raises(GraphAuthError):
        MicrosoftGraphClient.from_env(environ={})


def test_microsoft_graph_client_empty_token() -> None:
    with pytest.raises(GraphAuthError):
        MicrosoftGraphClient(access_token="")


def test_microsoft_graph_client_from_env_present() -> None:
    client = MicrosoftGraphClient.from_env(
        environ={"SPAUTOPOST_GRAPH_ACCESS_TOKEN": "test-token-xyz"}
    )
    assert isinstance(client, MicrosoftGraphClient)


# ---------------------------------------------------------------------------
# publish_approved_draft — status guard
# ---------------------------------------------------------------------------


def test_publish_rejects_non_approved_status(tmp_path: Path) -> None:
    storage = _build_sqlite_storage(tmp_path)
    draft = _make_draft(status="generated")
    storage.draft_posts.upsert(draft)

    with pytest.raises(PublishError, match="status='generated'"):
        publish_approved_draft(
            draft=draft,
            storage=storage,
            graph=NoopGraphClient(),
            target_site_id="site-1",
            target_page_library_id="lib-1",
            actor="alice",
        )

    # Nothing changed
    stored = storage.draft_posts.get(draft.draft_id)
    assert stored is not None
    assert stored.status == "generated"
    storage.close()


def test_publish_rejects_published_status(tmp_path: Path) -> None:
    storage = _build_sqlite_storage(tmp_path)
    draft = _make_draft(status="published")
    storage.draft_posts.upsert(draft)

    with pytest.raises(PublishError):
        publish_approved_draft(
            draft=draft,
            storage=storage,
            graph=NoopGraphClient(),
            target_site_id="site-1",
            target_page_library_id="lib-1",
            actor="alice",
        )
    storage.close()


# ---------------------------------------------------------------------------
# publish_approved_draft — dry-run
# ---------------------------------------------------------------------------


def test_publish_dry_run_no_graph_call(tmp_path: Path) -> None:
    storage = _build_sqlite_storage(tmp_path)
    draft = _make_draft()
    storage.draft_posts.upsert(draft)

    calls: list[str] = []

    class SpyGraphClient:
        def create_news_article(self, *, site_id: str, title: str, html_content: str) -> GraphPage:
            calls.append(site_id)
            return GraphPage(page_id="spy-page")

    result = publish_approved_draft(
        draft=draft,
        storage=storage,
        graph=SpyGraphClient(),
        target_site_id="site-1",
        target_page_library_id="lib-1",
        actor="alice",
        dry_run=True,
    )

    assert calls == [], "Graph must not be called in dry-run"
    assert result.publication.publication_status == "dry_run"
    assert result.audit_event.event_type == "publish_dry_run"
    assert result.audit_event.result == "success"

    # DraftPost status must NOT change
    stored = storage.draft_posts.get(draft.draft_id)
    assert stored is not None
    assert stored.status == "approved"
    storage.close()


def test_publish_dry_run_publication_recorded(tmp_path: Path) -> None:
    storage = _build_sqlite_storage(tmp_path)
    draft = _make_draft()
    storage.draft_posts.upsert(draft)

    result = publish_approved_draft(
        draft=draft,
        storage=storage,
        graph=NoopGraphClient(),
        target_site_id="site-1",
        target_page_library_id="lib-1",
        actor="alice",
        dry_run=True,
        correlation_id="corr-dry",
    )

    pub = storage.publications.get(result.publication.publication_id)
    assert pub is not None
    assert pub.publication_status == "dry_run"
    assert pub.operation == "dry-run"
    assert pub.target_site_id == "site-1"
    assert pub.idempotency_key.startswith("pub:")
    storage.close()


# ---------------------------------------------------------------------------
# publish_approved_draft — real publish (success)
# ---------------------------------------------------------------------------


def test_publish_success(tmp_path: Path) -> None:
    storage = _build_sqlite_storage(tmp_path)
    draft = _make_draft()
    storage.draft_posts.upsert(draft)

    result = publish_approved_draft(
        draft=draft,
        storage=storage,
        graph=NoopGraphClient(),
        target_site_id="site-1",
        target_page_library_id="lib-1",
        actor="alice",
        service_principal="svc-principal",
        dry_run=False,
        correlation_id="corr-1",
    )

    assert result.created is True
    assert result.publication.publication_status == "published"
    assert result.publication.sharepoint_page_id == "noop-page-id"
    assert result.publication.operation == "publish"
    assert result.audit_event.event_type == "publish_result"
    assert result.audit_event.result == "success"
    assert result.audit_event.actor == "alice"
    assert result.audit_event.service_principal == "svc-principal"

    # DraftPost must be published
    stored_draft = storage.draft_posts.get(draft.draft_id)
    assert stored_draft is not None
    assert stored_draft.status == "published"

    # Publication persisted
    stored_pub = storage.publications.get(result.publication.publication_id)
    assert stored_pub is not None
    assert stored_pub.publication_status == "published"
    storage.close()


def test_publish_audit_event_related_ids(tmp_path: Path) -> None:
    storage = _build_sqlite_storage(tmp_path)
    draft = _make_draft()
    storage.draft_posts.upsert(draft)

    result = publish_approved_draft(
        draft=draft,
        storage=storage,
        graph=NoopGraphClient(),
        target_site_id="site-1",
        target_page_library_id="lib-1",
        actor="bob",
        dry_run=False,
    )

    related = result.audit_event.related_ids
    assert related is not None
    assert related.get("draft_id") == draft.draft_id
    assert "adv-1" in related.get("advisory_ids", [])
    storage.close()


# ---------------------------------------------------------------------------
# publish_approved_draft — idempotency
# ---------------------------------------------------------------------------


def test_publish_idempotency_second_call_returns_existing(tmp_path: Path) -> None:
    storage = _build_sqlite_storage(tmp_path)
    draft = _make_draft()
    storage.draft_posts.upsert(draft)

    result1 = publish_approved_draft(
        draft=draft,
        storage=storage,
        graph=NoopGraphClient(),
        target_site_id="site-1",
        target_page_library_id="lib-1",
        actor="alice",
        dry_run=False,
    )

    # Second call: draft is now "published", so update our local reference
    updated_draft = storage.draft_posts.get(draft.draft_id)
    assert updated_draft is not None

    # Simulate re-calling with the original approved draft (as if caller didn't re-fetch)
    # The idempotency key is the same; existing Publication status=published → skip
    result2 = publish_approved_draft(
        draft=dataclasses.replace(draft, status="approved"),  # re-provide as approved
        storage=storage,
        graph=NoopGraphClient(),
        target_site_id="site-1",
        target_page_library_id="lib-1",
        actor="alice",
        dry_run=False,
    )

    assert result2.created is False
    assert result2.publication.publication_id == result1.publication.publication_id
    assert result2.audit_event.result == "skipped"
    storage.close()


# ---------------------------------------------------------------------------
# publish_approved_draft — failure
# ---------------------------------------------------------------------------


def test_publish_graph_failure(tmp_path: Path) -> None:
    storage = _build_sqlite_storage(tmp_path)
    draft = _make_draft()
    storage.draft_posts.upsert(draft)

    class FailingGraphClient:
        def create_news_article(self, *, site_id: str, title: str, html_content: str) -> GraphPage:
            raise RuntimeError("Graph API timeout")

    with pytest.raises(PublishError, match="SharePoint publish failed"):
        publish_approved_draft(
            draft=draft,
            storage=storage,
            graph=FailingGraphClient(),
            target_site_id="site-1",
            target_page_library_id="lib-1",
            actor="alice",
            dry_run=False,
        )

    # DraftPost must be "failed"
    stored_draft = storage.draft_posts.get(draft.draft_id)
    assert stored_draft is not None
    assert stored_draft.status == "failed"

    # Publication must be "failed"
    pubs = storage.publications.list()
    assert len(pubs) == 1
    assert pubs[0].publication_status == "failed"
    assert pubs[0].retryable is True
    assert pubs[0].error_code == "RuntimeError"

    # AuditEvent must record failure
    audits = storage.audit_events.list()
    assert len(audits) == 1
    assert audits[0].event_type == "publish_result"
    assert audits[0].result == "failure"
    storage.close()


# ---------------------------------------------------------------------------
# publish_approved_draft — publish result contains site info in audit
# ---------------------------------------------------------------------------


def test_publish_audit_event_site_info(tmp_path: Path) -> None:
    storage = _build_sqlite_storage(tmp_path)
    draft = _make_draft()
    storage.draft_posts.upsert(draft)

    result = publish_approved_draft(
        draft=draft,
        storage=storage,
        graph=NoopGraphClient(),
        target_site_id="my-site-id",
        target_page_library_id="my-lib-id",
        actor="alice",
        dry_run=False,
    )

    assert result.audit_event.target_site_id == "my-site-id"
    assert result.audit_event.target_page_library_id == "my-lib-id"
    assert result.audit_event.sharepoint_page_id == "noop-page-id"
    assert result.audit_event.idempotency_key.startswith("pub:")
    storage.close()


# ---------------------------------------------------------------------------
# publish_approved_draft — idempotency replay with published draft
# ---------------------------------------------------------------------------


def test_publish_replay_with_published_draft_returns_existing(tmp_path: Path) -> None:
    """Replaying publish_request with the already-published draft must not raise."""
    storage = _build_sqlite_storage(tmp_path)
    draft = _make_draft()
    storage.draft_posts.upsert(draft)

    result1 = publish_approved_draft(
        draft=draft,
        storage=storage,
        graph=NoopGraphClient(),
        target_site_id="site-1",
        target_page_library_id="lib-1",
        actor="alice",
        dry_run=False,
    )

    # After publish, reload the draft — its status is now "published"
    published_draft = storage.draft_posts.get(draft.draft_id)
    assert published_draft is not None
    assert published_draft.status == "published"

    # Replay with the published draft; idempotency pre-check must return existing
    result2 = publish_approved_draft(
        draft=published_draft,
        storage=storage,
        graph=NoopGraphClient(),
        target_site_id="site-1",
        target_page_library_id="lib-1",
        actor="alice",
        dry_run=False,
    )

    assert result2.created is False
    assert result2.publication.publication_id == result1.publication.publication_id
    assert result2.audit_event.result == "skipped"
    storage.close()


def test_publish_success_clears_failure_metadata(tmp_path: Path) -> None:
    """A retry after a prior failure must not carry stale error_code/error_message."""
    storage = _build_sqlite_storage(tmp_path)
    draft = _make_draft()
    storage.draft_posts.upsert(draft)

    call_count = 0

    class FirstFailThenSucceedClient:
        def create_news_article(self, *, site_id: str, title: str, html_content: str) -> GraphPage:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("transient failure")
            return GraphPage(page_id="retry-page-id")

    # First attempt fails
    with pytest.raises(PublishError):
        publish_approved_draft(
            draft=draft,
            storage=storage,
            graph=FirstFailThenSucceedClient(),
            target_site_id="site-1",
            target_page_library_id="lib-1",
            actor="alice",
            dry_run=False,
        )

    # Reset the persisted failed draft to approved so the retry mirrors production state
    failed_draft = storage.draft_posts.get(draft.draft_id)
    assert failed_draft is not None
    storage.draft_posts.upsert(dataclasses.replace(failed_draft, status="approved"))
    draft_retried = storage.draft_posts.get(draft.draft_id)
    assert draft_retried is not None

    result = publish_approved_draft(
        draft=draft_retried,
        storage=storage,
        graph=FirstFailThenSucceedClient(),
        target_site_id="site-1",
        target_page_library_id="lib-1",
        actor="alice",
        dry_run=False,
    )

    assert result.publication.publication_status == "published"
    assert result.publication.error_code is None
    assert result.publication.error_message is None
    assert result.publication.retryable is None
    storage.close()


# ---------------------------------------------------------------------------
# _ref_item / _safe_href — XSS via javascript: URLs
# ---------------------------------------------------------------------------


def test_build_page_html_javascript_url_is_sanitized() -> None:
    """javascript: URLs in references must not appear in href."""
    draft = dataclasses.replace(
        _make_draft(),
        references=[{"url": "javascript:alert(1)", "label": "evil"}],
    )
    html = build_page_html(draft)
    assert "javascript:" not in html
    assert 'href="#"' in html


def test_build_page_html_https_url_is_preserved() -> None:
    """Safe https:// URLs in references must be kept in href."""
    draft = dataclasses.replace(
        _make_draft(),
        references=[{"url": "https://example.com/safe", "label": "safe link"}],
    )
    html = build_page_html(draft)
    assert 'href="https://example.com/safe"' in html


def test_build_page_html_newlines_become_br() -> None:
    """Newlines in summary_for_users and impact must be converted to <br />."""
    draft = dataclasses.replace(
        _make_draft(),
        summary_for_users="line1\nline2",
        impact="a\nb",
    )
    html = build_page_html(draft)
    assert "<br />" in html
    assert "line1<br />line2" in html
