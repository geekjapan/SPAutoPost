"""Unit tests for the delegated-permission SharePoint Site Page connector.

No live Microsoft Graph and no real token: the transport and token provider are
fakes. Covers draft create, dry-run no-op, approval guard, Graph error
classification, idempotency skip, secret non-leakage, and HTML escaping.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from itertools import count
from typing import Any

import pytest

from spautopost.sharepoint_connector import (
    ConnectorError,
    GraphHttpResponse,
    GraphTransportError,
    SharePointConnector,
    _ascii_slug,
    _list_section,
    build_idempotency_key,
    build_site_page_payload,
    classify_graph_status,
    render_page_html,
    urllib_transport,
)
from spautopost.storage.models import DraftPost, Publication

NOW = datetime(2026, 6, 26, 9, 0, tzinfo=UTC)
TOKEN = "delegated-secret-token-value"  # noqa: S105 (test fixture, not a real secret)
SITE_ID = "contoso.sharepoint.com,site-guid,web-guid"
PAGE_LIBRARY_ID = "page-library-guid"


def _ids() -> Any:
    counter = count(1)
    return lambda: f"id-{next(counter)}"


def _approved_draft(**overrides: Any) -> DraftPost:
    base: dict[str, Any] = {
        "draft_id": "draft-1",
        "title": "重要なセキュリティ更新",
        "audience": "mixed",
        "urgency": "high",
        "summary_for_users": "概要本文",
        "impact": "影響本文",
        "status": "approved",
        "created_at": NOW,
        "updated_at": NOW,
        "advisory_ids": ("adv-1", "adv-2"),
        "required_actions": ("更新を適用する",),
        "admin_actions": ("配信を確認する",),
        "references": (
            {"label": "ベンダー情報", "url": "https://example.com/a", "type": "vendor"},
        ),
    }
    base.update(overrides)
    return DraftPost(**base)


class _FakeTransport:
    """Records calls and returns a queued response (or raises a queued error)."""

    def __init__(self, response: GraphHttpResponse | Exception) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Mapping[str, object] | None,
    ) -> GraphHttpResponse:
        self.calls.append({"method": method, "url": url, "headers": dict(headers), "body": body})
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


def _exploding_transport(*_args: Any, **_kwargs: Any) -> GraphHttpResponse:
    raise AssertionError("transport must not be called")


class _PublicationsFake:
    def __init__(self) -> None:
        self._by_key: dict[str, Publication] = {}

    def get_by_idempotency_key(self, idempotency_key: str) -> Publication | None:
        return self._by_key.get(idempotency_key)

    def create_if_absent(self, publication: Publication) -> tuple[Publication, bool]:
        existing = self._by_key.get(publication.idempotency_key)
        if existing is not None:
            return existing, False
        self._by_key[publication.idempotency_key] = publication
        return publication, True

    def upsert(self, publication: Publication) -> Publication:
        # Mirror real _PublicationRepository.upsert: update by PK when found,
        # else insert (which would UNIQUE-fail if idempotency_key already exists).
        existing_by_id = next(
            (p for p in self._by_key.values() if p.publication_id == publication.publication_id),
            None,
        )
        if existing_by_id is not None:
            self._by_key[existing_by_id.idempotency_key] = publication
        else:
            if publication.idempotency_key in self._by_key:
                raise ValueError(
                    f"upsert: UNIQUE violation on idempotency_key={publication.idempotency_key!r}"
                )
            self._by_key[publication.idempotency_key] = publication
        return publication


class _AuditFake:
    def __init__(self) -> None:
        self.events: list[Any] = []

    def append(self, event: Any) -> Any:
        self.events.append(event)
        return event


class _StoreFake:
    def __init__(self) -> None:
        self.publications = _PublicationsFake()
        self.audit_events = _AuditFake()


def _connector(transport: Any, *, dry_run: bool = False, store: Any = None) -> SharePointConnector:
    return SharePointConnector(
        transport=transport,
        token_provider=lambda: TOKEN,
        site_id=SITE_ID,
        page_library_id=PAGE_LIBRARY_ID,
        dry_run=dry_run,
        store=store,
        clock=lambda: NOW,
        id_factory=_ids(),
    )


@pytest.mark.unit
def test_approved_draft_is_created_as_site_page() -> None:
    transport = _FakeTransport(GraphHttpResponse(status=201, body={"id": "page-123"}))
    outcome = _connector(transport).publish_draft(
        _approved_draft(), approver="approver@contoso.com", publisher_principal="pub@contoso.com"
    )

    assert outcome.posted is True
    assert outcome.publication.publication_status == "published"
    assert outcome.publication.operation == "create"
    assert outcome.publication.target_type == "site-page"
    assert outcome.publication.sharepoint_page_id == "page-123"
    assert outcome.publication.published_at == NOW
    assert outcome.audit_event.event_type == "publish_create"
    assert outcome.audit_event.result == "success"
    assert outcome.audit_event.actor == "approver@contoso.com"
    assert outcome.audit_event.service_principal == "pub@contoso.com"

    assert len(transport.calls) == 1
    call = transport.calls[0]
    assert call["method"] == "POST"
    assert f"/sites/{SITE_ID}/pages" in call["url"]
    assert call["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert call["body"]["@odata.type"] == "#microsoft.graph.sitePage"


@pytest.mark.unit
def test_dry_run_performs_no_transport_call() -> None:
    outcome = _connector(_exploding_transport, dry_run=True).publish_draft(_approved_draft())

    assert outcome.posted is False
    assert outcome.publication.publication_status == "dry_run"
    assert outcome.publication.operation == "dry-run"
    assert outcome.publication.sharepoint_page_id is None
    assert outcome.audit_event.event_type == "publish_dry_run"
    assert outcome.audit_event.result == "success"
    blob = repr(outcome.publication) + repr(outcome.audit_event)
    assert TOKEN not in blob


@pytest.mark.unit
def test_non_approved_draft_is_rejected_before_any_graph_call() -> None:
    connector = _connector(_exploding_transport)
    with pytest.raises(ConnectorError) as exc:
        connector.publish_draft(_approved_draft(status="generated"))
    assert exc.value.error_code == "draft_not_approved"


@pytest.mark.unit
def test_missing_required_content_is_rejected() -> None:
    connector = _connector(_exploding_transport)
    with pytest.raises(ConnectorError) as exc:
        connector.publish_draft(_approved_draft(summary_for_users="   "))
    assert exc.value.error_code == "required_field_missing"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("status", "error_code", "retryable"),
    [
        (401, "graph_authentication_failed", False),
        (403, "graph_authorization_failed", False),
        (404, "target_site_not_found", False),
        (429, "graph_rate_limited", True),
        (500, "graph_timeout", True),
        (503, "graph_timeout", True),
    ],
)
def test_graph_failures_are_classified_and_recorded(
    status: int, error_code: str, retryable: bool
) -> None:
    transport = _FakeTransport(GraphHttpResponse(status=status, body={"error": "x"}))
    outcome = _connector(transport).publish_draft(_approved_draft())

    assert outcome.posted is False
    assert outcome.publication.publication_status == "failed"
    assert outcome.publication.error_code == error_code
    assert outcome.publication.retryable is retryable
    assert outcome.audit_event.event_type == "error"
    assert outcome.audit_event.result == "failure"
    # Secret hygiene: the token never appears in any recorded field.
    assert TOKEN not in (outcome.publication.error_message or "")
    assert TOKEN not in repr(outcome.audit_event)


@pytest.mark.unit
def test_transport_error_maps_to_retryable_timeout() -> None:
    transport = _FakeTransport(GraphTransportError("connection reset"))
    outcome = _connector(transport).publish_draft(_approved_draft())

    assert outcome.publication.publication_status == "failed"
    assert outcome.publication.error_code == "graph_timeout"
    assert outcome.publication.retryable is True


@pytest.mark.unit
def test_duplicate_publish_is_skipped_via_store() -> None:
    store = _StoreFake()
    draft = _approved_draft()
    key = build_idempotency_key(
        draft_id=draft.draft_id,
        site_id=SITE_ID,
        page_library_id=PAGE_LIBRARY_ID,
        advisory_ids=draft.advisory_ids,
        title=draft.title,
    )
    store.publications._by_key[key] = Publication(
        publication_id="existing",
        draft_id=draft.draft_id,
        target_type="site-page",
        target_site_id=SITE_ID,
        publication_status="published",
        idempotency_key=key,
        created_at=NOW,
        updated_at=NOW,
        sharepoint_page_id="page-existing",
    )
    outcome = _connector(_exploding_transport, store=store).publish_draft(draft)

    assert outcome.posted is False
    assert outcome.publication.publication_id == "existing"
    assert outcome.audit_event.error_code == "duplicate_detected"


@pytest.mark.unit
def test_outcome_is_persisted_through_store() -> None:
    store = _StoreFake()
    transport = _FakeTransport(GraphHttpResponse(status=201, body={"id": "page-9"}))
    outcome = _connector(transport, store=store).publish_draft(
        _approved_draft(), approver="a@contoso.com", publisher_principal="p@contoso.com"
    )

    stored = store.publications.get_by_idempotency_key(outcome.publication.idempotency_key)
    assert stored is not None
    assert stored.sharepoint_page_id == "page-9"
    assert len(store.audit_events.events) == 1


@pytest.mark.unit
def test_idempotency_key_is_deterministic_and_title_sensitive() -> None:
    args = {
        "draft_id": "d1",
        "site_id": SITE_ID,
        "page_library_id": PAGE_LIBRARY_ID,
        "advisory_ids": ["b", "a"],
    }
    k1 = build_idempotency_key(title="Title", **args)
    k2 = build_idempotency_key(title="Title", **args)
    k3 = build_idempotency_key(title="Different", **args)
    assert k1 == k2
    assert k1 != k3


@pytest.mark.unit
def test_render_page_html_escapes_draft_text() -> None:
    html_body = render_page_html(_approved_draft(title="<script>alert(1)</script>"))
    assert "<script>alert(1)</script>" not in html_body
    assert "&lt;script&gt;" in html_body


@pytest.mark.unit
def test_token_never_appears_in_recorded_outcome() -> None:
    transport = _FakeTransport(GraphHttpResponse(status=201, body={"id": "page-1"}))
    outcome = _connector(transport).publish_draft(_approved_draft())
    blob = repr(outcome.publication) + repr(outcome.audit_event)
    assert TOKEN not in blob


@pytest.mark.unit
def test_site_page_payload_uses_aspx_name_and_text_webpart() -> None:
    payload = build_site_page_payload(_approved_draft())
    assert str(payload["name"]).endswith(".aspx")
    section = payload["canvasLayout"]["horizontalSections"][0]  # type: ignore[index]
    webpart = section["columns"][0]["webparts"][0]
    assert webpart["@odata.type"] == "#microsoft.graph.textWebPart"


@pytest.mark.unit
def test_classify_graph_status_unknown_is_non_retryable() -> None:
    assert classify_graph_status(400) == ("publish_failed", False)


@pytest.mark.unit
def test_classify_graph_status_408_is_retryable_timeout() -> None:
    assert classify_graph_status(408) == ("graph_timeout", True)


@pytest.mark.unit
def test_references_javascript_and_data_urls_are_rejected() -> None:
    draft = _approved_draft(
        references=(
            {"label": "safe", "url": "https://example.com/advisory"},
            {"label": "xss", "url": "javascript:alert(document.domain)"},
            {"label": "data", "url": "data:text/html,<script>x=1</script>"},
        ),
    )
    rendered = render_page_html(draft)
    assert "javascript:" not in rendered
    assert "data:" not in rendered
    assert "https://example.com/advisory" in rendered


@pytest.mark.unit
def test_urllib_transport_rejects_non_https() -> None:
    with pytest.raises(GraphTransportError):
        urllib_transport("POST", "http://insecure/api", {}, {"a": 1})


# --- regression tests for review-comment fixes ---


@pytest.mark.unit
def test_successful_retry_updates_failed_publication_to_published() -> None:
    """A previously-failed publication must be overwritten on successful retry."""
    store = _StoreFake()
    draft = _approved_draft()
    key = build_idempotency_key(
        draft_id=draft.draft_id,
        site_id=SITE_ID,
        page_library_id=PAGE_LIBRARY_ID,
        advisory_ids=draft.advisory_ids,
        title=draft.title,
    )
    store.publications._by_key[key] = Publication(
        publication_id="prev-failed",
        draft_id=draft.draft_id,
        target_type="site-page",
        target_site_id=SITE_ID,
        publication_status="failed",
        idempotency_key=key,
        created_at=NOW,
        updated_at=NOW,
        error_code="graph_timeout",
        retryable=True,
        operation="create",
    )
    transport = _FakeTransport(GraphHttpResponse(status=201, body={"id": "page-retry"}))
    outcome = _connector(transport, store=store).publish_draft(draft)

    assert outcome.posted is True
    assert outcome.publication.publication_status == "published"
    assert outcome.publication.sharepoint_page_id == "page-retry"
    stored = store.publications.get_by_idempotency_key(key)
    assert stored is not None
    assert stored.publication_status == "published"


@pytest.mark.unit
def test_concurrent_publishing_reservation_prevents_duplicate_post() -> None:
    """A 'publishing' row written by another worker must be treated as a duplicate."""
    store = _StoreFake()
    draft = _approved_draft()
    key = build_idempotency_key(
        draft_id=draft.draft_id,
        site_id=SITE_ID,
        page_library_id=PAGE_LIBRARY_ID,
        advisory_ids=draft.advisory_ids,
        title=draft.title,
    )
    store.publications._by_key[key] = Publication(
        publication_id="in-flight",
        draft_id=draft.draft_id,
        target_type="site-page",
        target_site_id=SITE_ID,
        publication_status="publishing",
        idempotency_key=key,
        created_at=NOW,
        updated_at=NOW,
        operation="create",
    )
    outcome = _connector(_exploding_transport, store=store).publish_draft(draft)

    assert outcome.posted is False
    assert outcome.publication.publication_id == "in-flight"
    assert outcome.audit_event.error_code == "duplicate_detected"


@pytest.mark.unit
def test_ascii_slug_strips_non_ascii_alphanumeric() -> None:
    assert _ascii_slug("draft-あ") == "draft"
    assert _ascii_slug("hello-world") == "hello-world"
    assert _ascii_slug("CVE-2024-漢字") == "cve-2024"
    assert _ascii_slug("") == "page"


@pytest.mark.unit
def test_list_section_with_none_items_returns_empty_string() -> None:
    assert _list_section("Heading", None) == ""


@pytest.mark.unit
def test_references_none_label_falls_back_to_url() -> None:
    draft = _approved_draft(
        references=({"label": None, "url": "https://example.com/doc"},),  # type: ignore[arg-type]
    )
    rendered = render_page_html(draft)
    assert "None" not in rendered
    assert "https://example.com/doc" in rendered


@pytest.mark.unit
def test_empty_required_actions_is_rejected() -> None:
    connector = _connector(_exploding_transport)
    with pytest.raises(ConnectorError) as exc:
        connector.publish_draft(_approved_draft(required_actions=()))
    assert exc.value.error_code == "required_field_missing"


@pytest.mark.unit
def test_whitespace_only_required_action_is_rejected() -> None:
    connector = _connector(_exploding_transport)
    with pytest.raises(ConnectorError) as exc:
        connector.publish_draft(_approved_draft(required_actions=("   ",)))
    assert exc.value.error_code == "required_field_missing"


@pytest.mark.unit
def test_empty_references_is_rejected() -> None:
    connector = _connector(_exploding_transport)
    with pytest.raises(ConnectorError) as exc:
        connector.publish_draft(_approved_draft(references=()))
    assert exc.value.error_code == "required_field_missing"


@pytest.mark.unit
def test_references_without_valid_url_is_rejected() -> None:
    connector = _connector(_exploding_transport)
    with pytest.raises(ConnectorError) as exc:
        connector.publish_draft(
            _approved_draft(references=({"label": "bad", "url": "javascript:void(0)"},))
        )
    assert exc.value.error_code == "required_field_missing"


@pytest.mark.unit
def test_claim_id_is_reused_after_failed_row_on_successful_retry() -> None:
    """Final publication must carry the same publication_id as the failed-row claim."""
    store = _StoreFake()
    draft = _approved_draft()
    key = build_idempotency_key(
        draft_id=draft.draft_id,
        site_id=SITE_ID,
        page_library_id=PAGE_LIBRARY_ID,
        advisory_ids=draft.advisory_ids,
        title=draft.title,
    )
    original_id = "original-failed-id"
    store.publications._by_key[key] = Publication(
        publication_id=original_id,
        draft_id=draft.draft_id,
        target_type="site-page",
        target_site_id=SITE_ID,
        publication_status="failed",
        idempotency_key=key,
        created_at=NOW,
        updated_at=NOW,
        error_code="graph_timeout",
        retryable=True,
        operation="create",
    )
    transport = _FakeTransport(GraphHttpResponse(status=201, body={"id": "page-claim-retry"}))
    outcome = _connector(transport, store=store).publish_draft(draft)

    assert outcome.publication.publication_id == original_id
    stored = store.publications.get_by_idempotency_key(key)
    assert stored is not None
    assert stored.publication_id == original_id
    assert stored.publication_status == "published"


@pytest.mark.unit
def test_repeated_dry_run_reuses_existing_publication_id() -> None:
    """Second dry-run of the same draft must not raise a UNIQUE violation.

    The real storage backends enforce a UNIQUE constraint on idempotency_key and
    upsert by publication_id (PK).  A second dry-run that mints a fresh
    publication_id would hit the constraint; reusing the prior id lets upsert
    UPDATE the existing row in-place.
    """
    store = _StoreFake()
    draft = _approved_draft()
    connector = _connector(_exploding_transport, dry_run=True, store=store)

    first = connector.publish_draft(draft)
    assert first.publication.publication_status == "dry_run"
    first_id = first.publication.publication_id

    # Second dry-run — must not raise, must reuse the same publication_id.
    second = connector.publish_draft(draft)
    assert second.publication.publication_status == "dry_run"
    assert second.publication.publication_id == first_id
