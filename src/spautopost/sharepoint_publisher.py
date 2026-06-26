"""SharePoint News article publisher for approved DraftPosts.

M1 publish path:
  approved DraftPost → SharePoint Site Page / News → Publication + AuditEvent

Graph API is behind GraphClient Protocol (testable with NoopGraphClient or mocks).
Real implementation: MicrosoftGraphClient (requires SPAUTOPOST_GRAPH_ACCESS_TOKEN).

正本: docs/specs/sharepoint-publishing.md / docs/specs/data-model.md
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import urllib.error
import urllib.request
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import NamedTuple, Protocol, runtime_checkable

from .errors import GraphAuthError, PublishError
from .storage.models import AuditEvent, DraftPost, Publication, PublicationOperation
from .storage.port import StoragePort

# ---------------------------------------------------------------------------
# GraphClient abstraction
# ---------------------------------------------------------------------------


class GraphPage(NamedTuple):
    """Result of a successful page creation in Microsoft Graph."""

    page_id: str


@runtime_checkable
class GraphClient(Protocol):
    """Abstraction over Microsoft Graph for SharePoint Site Page creation."""

    def create_news_article(
        self,
        *,
        site_id: str,
        title: str,
        html_content: str,
    ) -> GraphPage:
        """Create a SharePoint News article and return its Graph page ID."""
        ...


class NoopGraphClient:
    """GraphClient that does nothing — for dry-run and unit tests."""

    def create_news_article(
        self,
        *,
        site_id: str,
        title: str,
        html_content: str,
    ) -> GraphPage:
        return GraphPage(page_id="noop-page-id")


class MicrosoftGraphClient:
    """Real Microsoft Graph client using stdlib urllib + bearer token.

    Token acquisition (MSAL / managed identity) is Issue #32 / #27.
    M1 local PoC: provide SPAUTOPOST_GRAPH_ACCESS_TOKEN as a pre-obtained token.
    """

    _GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(self, *, access_token: str) -> None:
        if not access_token or not access_token.strip():
            raise GraphAuthError("Microsoft Graph access token must not be empty")
        self._token = access_token

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> MicrosoftGraphClient:
        """Build from SPAUTOPOST_GRAPH_ACCESS_TOKEN environment variable."""
        import os

        env: Mapping[str, str] = environ if environ is not None else os.environ
        token = env.get("SPAUTOPOST_GRAPH_ACCESS_TOKEN", "")
        if not token:
            raise GraphAuthError(
                "SPAUTOPOST_GRAPH_ACCESS_TOKEN is required for Microsoft Graph API calls"
            )
        return cls(access_token=token)

    def create_news_article(
        self,
        *,
        site_id: str,
        title: str,
        html_content: str,
    ) -> GraphPage:
        """POST /sites/{site_id}/pages to create a News article, then publish it."""
        url = f"{self._GRAPH_BASE}/sites/{site_id}/pages"
        page_name = f"spautopost-{uuid.uuid4().hex[:8]}"
        body: dict[str, object] = {
            "@odata.type": "#microsoft.graph.sitePage",
            "name": f"{page_name}.aspx",
            "title": title,
            "promotionKind": "newsPost",
            "canvasLayout": {
                "horizontalSections": [
                    {
                        "layout": "oneColumn",
                        "id": "1",
                        "columns": [
                            {
                                "id": "1",
                                "width": 12,
                                "webparts": [
                                    {
                                        "@odata.type": "#microsoft.graph.textWebPart",
                                        "innerHtml": html_content,
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
        }
        response_data = self._post_json(url, body)
        page_id = str(response_data.get("id", ""))
        if not page_id:
            raise PublishError(
                f"Graph API did not return a page id; response: {list(response_data)!r}"
            )
        # Publish the page (promote from draft to published news post)
        publish_url = f"{url}/{page_id}/microsoft.graph.sitePage/publish"
        self._post_empty(publish_url)
        return GraphPage(page_id=page_id)

    def _post_json(self, url: str, body: dict[str, object]) -> dict[str, object]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                raw: object = json.loads(resp.read())
                return raw if isinstance(raw, dict) else {}
        except urllib.error.HTTPError as exc:
            snippet = exc.read().decode("utf-8", errors="replace")[:200]
            raise PublishError(f"Graph API returned HTTP {exc.code}: {snippet}") from exc
        except urllib.error.URLError as exc:
            raise PublishError(f"Graph API network error: {exc.reason}") from exc

    def _post_empty(self, url: str) -> None:
        """POST with no request body and no response body (publish endpoint returns 204)."""
        req = urllib.request.Request(  # noqa: S310
            url,
            data=b"",
            headers={"Authorization": f"Bearer {self._token}"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=30)  # noqa: S310
        except urllib.error.HTTPError as exc:
            snippet = exc.read().decode("utf-8", errors="replace")[:200]
            raise PublishError(f"Graph API publish returned HTTP {exc.code}: {snippet}") from exc
        except urllib.error.URLError as exc:
            raise PublishError(f"Graph API publish network error: {exc.reason}") from exc


# ---------------------------------------------------------------------------
# Content builder
# ---------------------------------------------------------------------------


def build_page_html(draft: DraftPost) -> str:
    """Build a minimal HTML body for a SharePoint Site Page from a DraftPost."""
    parts: list[str] = []
    parts.append(f"<h2>概要</h2><p>{_esc(draft.summary_for_users)}</p>")
    parts.append(f"<h2>影響</h2><p>{_esc(draft.impact)}</p>")
    if draft.required_actions:
        items = "".join(f"<li>{_esc(a)}</li>" for a in draft.required_actions)
        parts.append(f"<h2>利用者が行う対応</h2><ul>{items}</ul>")
    if draft.admin_actions:
        items = "".join(f"<li>{_esc(a)}</li>" for a in draft.admin_actions)
        parts.append(f"<h2>管理者が行う対応</h2><ul>{items}</ul>")
    if draft.references:
        ref_items = "".join(_ref_item(r) for r in draft.references)
        parts.append(f"<h2>参考情報</h2><ul>{ref_items}</ul>")
    return "".join(parts)


def _ref_item(ref: Mapping[str, str]) -> str:
    url = _esc(ref.get("url", ""))
    label = _esc(ref.get("label", ref.get("url", "")))
    return f'<li><a href="{url}">{label}</a></li>'


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# Idempotency key
# ---------------------------------------------------------------------------


def build_idempotency_key(
    *,
    draft_id: str,
    target_site_id: str,
    target_page_library_id: str,
) -> str:
    """Build a deterministic idempotency key for a publication attempt.

    Combines draft_id + target identifiers so the same draft cannot be
    published twice to the same site/library.
    """
    raw = f"{draft_id}:{target_site_id}:{target_page_library_id}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:32]
    # Prefix with draft_id prefix for human readability in DB queries
    return f"pub:{draft_id[:8]}:{digest}"


# ---------------------------------------------------------------------------
# Publisher
# ---------------------------------------------------------------------------


class PublishResult(NamedTuple):
    """Outcome of a publish_approved_draft() call."""

    publication: Publication
    audit_event: AuditEvent
    created: bool  # False = deduplicated (already published/publishing)


def publish_approved_draft(
    *,
    draft: DraftPost,
    storage: StoragePort,
    graph: GraphClient,
    target_site_id: str,
    target_page_library_id: str,
    actor: str,
    service_principal: str | None = None,
    dry_run: bool = False,
    correlation_id: str | None = None,
) -> PublishResult:
    """Publish an approved DraftPost as a SharePoint Site Page / News article.

    Safety gates:
    - draft.status must be 'approved'
    - dry_run=True: records dry_run Publication + AuditEvent; no Graph call; DraftPost unchanged
    - Idempotency: existing published/publishing Publication → returns existing, no re-publish

    Returns:
        PublishResult with publication, audit_event, and created flag.

    Raises:
        PublishError: if draft is not approved, or Graph API call fails.
    """
    if draft.status != "approved":
        raise PublishError(
            f"DraftPost {draft.draft_id!r} cannot be published: "
            f"status={draft.status!r} (expected 'approved')"
        )

    now = datetime.now(UTC)
    corr_id = correlation_id or uuid.uuid4().hex
    idem_key = build_idempotency_key(
        draft_id=draft.draft_id,
        target_site_id=target_site_id,
        target_page_library_id=target_page_library_id,
    )

    initial_operation: PublicationOperation = "dry-run" if dry_run else "create"
    initial_status = "dry_run" if dry_run else "publishing"

    initial_pub = Publication(
        publication_id=uuid.uuid4().hex,
        draft_id=draft.draft_id,
        target_type="site-page",
        target_site_id=target_site_id,
        target_page_library_id=target_page_library_id,
        publication_status=initial_status,  # type: ignore[arg-type]
        idempotency_key=idem_key,
        operation=initial_operation,
        created_at=now,
        updated_at=now,
    )

    pub, created = storage.publications.create_if_absent(initial_pub)

    # Idempotency: already published or in-progress → skip with a skipped audit event
    if not created and pub.publication_status in ("published", "publishing"):
        audit = _make_audit_event(
            event_type="publish_result",
            result="skipped",
            correlation_id=corr_id,
            now=now,
            actor=actor,
            service_principal=service_principal,
            draft=draft,
            pub=pub,
            idem_key=idem_key,
        )
        storage.audit_events.append(audit)
        return PublishResult(publication=pub, audit_event=audit, created=False)

    # Dry-run path: record outcome, no Graph call, no DraftPost status change
    if dry_run:
        audit = _make_audit_event(
            event_type="publish_dry_run",
            result="success",
            correlation_id=corr_id,
            now=now,
            actor=actor,
            service_principal=service_principal,
            draft=draft,
            pub=pub,
            idem_key=idem_key,
        )
        storage.audit_events.append(audit)
        return PublishResult(publication=pub, audit_event=audit, created=created)

    # Transition DraftPost → publishing
    publishing_draft = dataclasses.replace(draft, status="publishing", updated_at=now)
    storage.draft_posts.upsert(publishing_draft)

    try:
        page = graph.create_news_article(
            site_id=target_site_id,
            title=draft.title,
            html_content=build_page_html(draft),
        )

        done_now = datetime.now(UTC)
        published_pub = dataclasses.replace(
            pub,
            publication_status="published",
            sharepoint_page_id=page.page_id,
            published_at=done_now,
            operation="publish",
            updated_at=done_now,
        )
        storage.publications.upsert(published_pub)

        published_draft = dataclasses.replace(draft, status="published", updated_at=done_now)
        storage.draft_posts.upsert(published_draft)

        audit = _make_audit_event(
            event_type="publish_result",
            result="success",
            correlation_id=corr_id,
            now=done_now,
            actor=actor,
            service_principal=service_principal,
            draft=draft,
            pub=published_pub,
            idem_key=idem_key,
        )
        storage.audit_events.append(audit)
        return PublishResult(publication=published_pub, audit_event=audit, created=created)

    except Exception as exc:
        fail_now = datetime.now(UTC)
        error_code = type(exc).__name__
        error_message = str(exc)[:500]

        failed_pub = dataclasses.replace(
            pub,
            publication_status="failed",
            error_code=error_code,
            error_message=error_message,
            retryable=True,
            updated_at=fail_now,
        )
        storage.publications.upsert(failed_pub)

        failed_draft = dataclasses.replace(draft, status="failed", updated_at=fail_now)
        storage.draft_posts.upsert(failed_draft)

        audit = _make_audit_event(
            event_type="publish_result",
            result="failure",
            correlation_id=corr_id,
            now=fail_now,
            actor=actor,
            service_principal=service_principal,
            draft=draft,
            pub=failed_pub,
            idem_key=idem_key,
            error_code=error_code,
            error_message=error_message,
        )
        storage.audit_events.append(audit)

        raise PublishError(f"SharePoint publish failed: {exc}") from exc


def _make_audit_event(
    *,
    event_type: str,
    result: str,
    correlation_id: str,
    now: datetime,
    actor: str,
    service_principal: str | None,
    draft: DraftPost,
    pub: Publication,
    idem_key: str,
    error_code: str | None = None,
    error_message: str | None = None,
) -> AuditEvent:
    related: dict[str, object] = {"draft_id": draft.draft_id}
    if draft.advisory_ids:
        related["advisory_ids"] = list(draft.advisory_ids)
    return AuditEvent(
        audit_event_id=uuid.uuid4().hex,
        event_type=event_type,  # type: ignore[arg-type]
        correlation_id=correlation_id,
        result=result,  # type: ignore[arg-type]
        created_at=now,
        actor=actor,
        service_principal=service_principal,
        target_site_id=pub.target_site_id,
        target_page_library_id=pub.target_page_library_id,
        sharepoint_page_id=pub.sharepoint_page_id,
        idempotency_key=idem_key,
        operation=pub.operation,
        related_ids=related,
        error_code=error_code,
        error_message=error_message,
    )


__all__ = [
    "GraphClient",
    "GraphPage",
    "MicrosoftGraphClient",
    "NoopGraphClient",
    "PublishResult",
    "build_idempotency_key",
    "build_page_html",
    "publish_approved_draft",
]
