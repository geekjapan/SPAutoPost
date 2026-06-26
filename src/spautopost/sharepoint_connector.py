"""SharePoint Site Page connector (delegated-permission local PoC).

Creates a SharePoint Site Page *draft* from an approved ``DraftPost`` through
Microsoft Graph. The HTTP transport and the delegated token provider are both
injectable so unit tests never call live Graph and never need a real token; a
default stdlib ``urllib`` transport (HTTPS only) is provided for real use.

Scope (Issue #9): client init, target config, dry-run, draft create, Publication
/ AuditEvent recording, idempotency, and Graph error classification. Real
delegated sign-in (MSAL device-code) and CLI wiring are Issue #32; News promote
(`/publish`), updates, and hosted-runtime auth (managed identity / app-only) are
deferred (#27 follow-ups).

正本: GitHub Issue #9 / docs/specs/graph-authentication.md /
docs/specs/sharepoint-publishing.md / docs/specs/error-handling.md /
openspec/changes/issue-9-implement-sharepoint-connector-poc/.
"""

from __future__ import annotations

import hashlib
import html
import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from .storage.models import (
    AuditEvent,
    AuditEventType,
    AuditResult,
    DraftPost,
    Publication,
    PublicationOperation,
)
from .storage.port import StoragePort

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
CONNECTOR_VERSION = "sharepoint-connector-v1"
HTTP_TIMEOUT_SECONDS = 30
APPROVED_STATUSES: frozenset[str] = frozenset({"approved"})

# draft-composition.md の必須セクション順（「対象」は DraftPost に専用 field が無いため除外）。
_SECTION_HEADINGS: tuple[tuple[str, str], ...] = (
    ("概要", "summary_for_users"),
    ("影響", "impact"),
)
_DEADLINE_UNSET = "未定（要確認）"

TokenProvider = Callable[[], str]
Clock = Callable[[], datetime]
IdFactory = Callable[[], str]


def _default_clock() -> datetime:
    return datetime.now(UTC)


def _default_id() -> str:
    return uuid4().hex


class ConnectorError(RuntimeError):
    """Connector precondition / usage failure (e.g. draft not approved).

    Carries a canonical ``error_code`` from docs/specs/error-handling.md. Secret
    values are never placed in the message.
    """

    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        super().__init__(f"{error_code}: {message}")


class GraphTransportError(RuntimeError):
    """Network / transport-level Graph failure (no HTTP status)."""


@dataclass(frozen=True)
class GraphHttpResponse:
    """Transport-agnostic HTTP response carrying parsed JSON."""

    status: int
    body: Mapping[str, object] = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)


class GraphTransport(Protocol):
    def __call__(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Mapping[str, object] | None,
    ) -> GraphHttpResponse: ...


@dataclass(frozen=True)
class PublishOutcome:
    """Result of a publish attempt: the recorded Publication, the AuditEvent, and
    whether a real Graph write was performed."""

    publication: Publication
    audit_event: AuditEvent
    posted: bool


@dataclass(frozen=True)
class SharePointConnector:
    """Delegated-auth SharePoint Site Page connector.

    The bearer token from ``token_provider`` is sent only in the ``Authorization``
    header; it is never logged, stored, or placed in any Publication / AuditEvent
    / error message.
    """

    transport: GraphTransport
    token_provider: TokenProvider
    site_id: str
    page_library_id: str | None = None
    tenant_id: str | None = None
    dry_run: bool = True
    store: StoragePort | None = None
    base_url: str = GRAPH_BASE_URL
    clock: Clock = _default_clock
    id_factory: IdFactory = _default_id

    def publish_draft(
        self,
        draft: DraftPost,
        *,
        advisory_ids: Sequence[str] = (),
        approver: str | None = None,
        publisher_principal: str | None = None,
        correlation_id: str | None = None,
    ) -> PublishOutcome:
        """Create (or dry-run preview) a SharePoint Site Page draft for ``draft``.

        Raises ``ConnectorError`` for precondition failures (not approved, missing
        required fields). Graph runtime failures are classified and *recorded* as a
        failed Publication rather than raised.
        """
        self._require_approved(draft)
        ids = tuple(advisory_ids) or tuple(draft.advisory_ids)
        key = build_idempotency_key(
            draft_id=draft.draft_id,
            site_id=self.site_id,
            page_library_id=self.page_library_id,
            advisory_ids=ids,
            title=draft.title,
        )
        now = self.clock()
        correlation = correlation_id or self.id_factory()

        duplicate = self._existing_duplicate(key)
        if duplicate is not None:
            return self._record_duplicate(
                duplicate, key, ids, now, correlation, approver, publisher_principal
            )

        if self.dry_run:
            return self._record_dry_run(
                draft, key, ids, now, correlation, approver, publisher_principal
            )

        return self._create_page(draft, key, ids, now, correlation, approver, publisher_principal)

    # --- precondition / idempotency ---------------------------------------

    def _require_approved(self, draft: DraftPost) -> None:
        if draft.status not in APPROVED_STATUSES:
            raise ConnectorError(
                "draft_not_approved",
                f"draft {draft.draft_id} has status {draft.status!r}; must be approved",
            )
        for heading, attr in _SECTION_HEADINGS:
            value = getattr(draft, attr)
            if not isinstance(value, str) or not value.strip():
                raise ConnectorError(
                    "required_field_missing",
                    f"draft {draft.draft_id} is missing required content for {heading}",
                )

    def _existing_duplicate(self, key: str) -> Publication | None:
        if self.store is None:
            return None
        existing = self.store.publications.get_by_idempotency_key(key)
        if existing is not None and existing.publication_status in {"published", "publishing"}:
            return existing
        return None

    # --- recording branches -----------------------------------------------

    def _record_duplicate(
        self,
        existing: Publication,
        key: str,
        advisory_ids: tuple[str, ...],
        now: datetime,
        correlation: str,
        approver: str | None,
        publisher_principal: str | None,
    ) -> PublishOutcome:
        audit = self._audit(
            event_type="publish_result",
            result="skipped",
            now=now,
            correlation=correlation,
            key=key,
            operation="create",
            draft_id=existing.draft_id,
            advisory_ids=advisory_ids,
            actor=approver,
            service_principal=publisher_principal,
            sharepoint_page_id=existing.sharepoint_page_id,
            error_code="duplicate_detected",
        )
        self._append_audit(audit)
        return PublishOutcome(publication=existing, audit_event=audit, posted=False)

    def _record_dry_run(
        self,
        draft: DraftPost,
        key: str,
        advisory_ids: tuple[str, ...],
        now: datetime,
        correlation: str,
        approver: str | None,
        publisher_principal: str | None,
    ) -> PublishOutcome:
        publication = Publication(
            publication_id=self.id_factory(),
            draft_id=draft.draft_id,
            target_type="site-page",
            target_site_id=self.site_id,
            publication_status="dry_run",
            idempotency_key=key,
            created_at=now,
            updated_at=now,
            target_page_library_id=self.page_library_id,
            operation="dry-run",
        )
        audit = self._audit(
            event_type="publish_dry_run",
            result="success",
            now=now,
            correlation=correlation,
            key=key,
            operation="dry-run",
            draft_id=draft.draft_id,
            advisory_ids=advisory_ids,
            actor=approver,
            service_principal=publisher_principal,
        )
        publication = self._persist(publication)
        self._append_audit(audit)
        return PublishOutcome(publication=publication, audit_event=audit, posted=False)

    def _create_page(
        self,
        draft: DraftPost,
        key: str,
        advisory_ids: tuple[str, ...],
        now: datetime,
        correlation: str,
        approver: str | None,
        publisher_principal: str | None,
    ) -> PublishOutcome:
        # Reserve the idempotency key atomically before calling Graph so that
        # concurrent workers sharing the same store cannot both pass the
        # _existing_duplicate check and each create a separate SharePoint page.
        if self.store is not None:
            reservation = Publication(
                publication_id=self.id_factory(),
                draft_id=draft.draft_id,
                target_type="site-page",
                target_site_id=self.site_id,
                publication_status="publishing",
                idempotency_key=key,
                created_at=now,
                updated_at=now,
                target_page_library_id=self.page_library_id,
                operation="create",
            )
            existing, created = self.store.publications.create_if_absent(reservation)
            if not created and existing.publication_status in {"published", "publishing"}:
                return self._record_duplicate(
                    existing, key, advisory_ids, now, correlation, approver, publisher_principal
                )
        payload = build_site_page_payload(draft)
        url = f"{self.base_url}/sites/{self.site_id}/pages"
        headers = {"Authorization": f"Bearer {self.token_provider()}"}
        try:
            response = self.transport("POST", url, headers, payload)
        except GraphTransportError:
            return self._record_failure(
                draft,
                key,
                advisory_ids,
                now,
                correlation,
                approver,
                publisher_principal=publisher_principal,
                error_code="graph_timeout",
                retryable=True,
                status=None,
            )

        if response.status in (200, 201):
            page_id = _optional_str(response.body, "id")
            # A created Graph page is a SharePoint *draft*; we record it as
            # publication_status="published" (the connector's write succeeded) with
            # operation="create" preserving the create-vs-promote distinction. News
            # promote (Graph /publish, operation="publish") is deferred to #20/#32.
            publication = Publication(
                publication_id=self.id_factory(),
                draft_id=draft.draft_id,
                target_type="site-page",
                target_site_id=self.site_id,
                publication_status="published",
                idempotency_key=key,
                created_at=now,
                updated_at=now,
                target_page_library_id=self.page_library_id,
                sharepoint_page_id=page_id,
                operation="create",
                published_at=now,
            )
            audit = self._audit(
                event_type="publish_create",
                result="success",
                now=now,
                correlation=correlation,
                key=key,
                operation="create",
                draft_id=draft.draft_id,
                advisory_ids=advisory_ids,
                actor=approver,
                service_principal=publisher_principal,
                sharepoint_page_id=page_id,
            )
            publication = self._persist(publication)
            self._append_audit(audit)
            return PublishOutcome(publication=publication, audit_event=audit, posted=True)

        error_code, retryable = classify_graph_status(response.status)
        return self._record_failure(
            draft,
            key,
            advisory_ids,
            now,
            correlation,
            approver,
            publisher_principal=publisher_principal,
            error_code=error_code,
            retryable=retryable,
            status=response.status,
        )

    def _record_failure(
        self,
        draft: DraftPost,
        key: str,
        advisory_ids: tuple[str, ...],
        now: datetime,
        correlation: str,
        approver: str | None,
        *,
        publisher_principal: str | None = None,
        error_code: str,
        retryable: bool,
        status: int | None,
    ) -> PublishOutcome:
        # Secret-free message: only the canonical code and HTTP status, never the
        # token or raw Graph body (which may echo request headers).
        message = (
            f"SharePoint create failed (HTTP {status})"
            if status is not None
            else "SharePoint create failed (transport error)"
        )
        publication = Publication(
            publication_id=self.id_factory(),
            draft_id=draft.draft_id,
            target_type="site-page",
            target_site_id=self.site_id,
            publication_status="failed",
            idempotency_key=key,
            created_at=now,
            updated_at=now,
            target_page_library_id=self.page_library_id,
            operation="create",
            error_code=error_code,
            error_message=message,
            retryable=retryable,
        )
        audit = self._audit(
            event_type="error",
            result="failure",
            now=now,
            correlation=correlation,
            key=key,
            operation="create",
            draft_id=draft.draft_id,
            advisory_ids=advisory_ids,
            actor=approver,
            service_principal=publisher_principal,
            error_code=error_code,
            error_message=message,
            retryable=retryable,
        )
        publication = self._persist(publication)
        self._append_audit(audit)
        return PublishOutcome(publication=publication, audit_event=audit, posted=False)

    # --- persistence + audit assembly -------------------------------------

    def _persist(self, publication: Publication) -> Publication:
        if self.store is None:
            return publication
        return self.store.publications.upsert(publication)

    def _append_audit(self, event: AuditEvent) -> None:
        if self.store is not None:
            self.store.audit_events.append(event)

    def _audit(
        self,
        *,
        event_type: AuditEventType,
        result: AuditResult,
        now: datetime,
        correlation: str,
        key: str,
        operation: PublicationOperation,
        draft_id: str,
        advisory_ids: tuple[str, ...],
        actor: str | None = None,
        service_principal: str | None = None,
        sharepoint_page_id: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        retryable: bool | None = None,
    ) -> AuditEvent:
        related: dict[str, object] = {"draft_id": draft_id}
        if advisory_ids:
            related["advisory_ids"] = list(advisory_ids)
        if retryable is not None:
            related["retryable"] = retryable
        return AuditEvent(
            audit_event_id=self.id_factory(),
            event_type=event_type,
            correlation_id=correlation,
            result=result,
            created_at=now,
            actor=actor,
            service_principal=service_principal,
            related_ids=related,
            target_site_id=self.site_id,
            target_page_library_id=self.page_library_id,
            sharepoint_page_id=sharepoint_page_id,
            idempotency_key=key,
            operation=operation,
            error_code=error_code,
            error_message=error_message,
        )


# --- idempotency / classification / rendering ------------------------------


def build_idempotency_key(
    *,
    draft_id: str,
    site_id: str,
    page_library_id: str | None,
    advisory_ids: Sequence[str],
    title: str,
) -> str:
    """Deterministic idempotency key (sharepoint-publishing.md recommended elements)."""
    title_hash = hashlib.sha256(title.strip().casefold().encode("utf-8")).hexdigest()
    parts = [
        draft_id,
        site_id,
        page_library_id or "",
        *sorted(advisory_ids),
        title_hash,
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def classify_graph_status(status: int) -> tuple[str, bool]:
    """Map a Graph HTTP status to (error_code, retryable) per error-handling.md."""
    mapping: dict[int, tuple[str, bool]] = {
        401: ("graph_authentication_failed", False),
        403: ("graph_authorization_failed", False),
        404: ("target_site_not_found", False),
        408: ("graph_timeout", True),
        429: ("graph_rate_limited", True),
    }
    if status in mapping:
        return mapping[status]
    if status >= 500:
        return ("graph_timeout", True)
    return ("publish_failed", False)


def build_site_page_payload(draft: DraftPost) -> dict[str, object]:
    """Build the Microsoft Graph ``sitePage`` create payload from a ``DraftPost``.

    Draft text is HTML-escaped into a single text web part. ``name`` is an ASCII
    slug derived from the draft id (Graph requires an ``.aspx`` name).
    """
    name = f"spautopost-{_ascii_slug(draft.draft_id)}.aspx"
    return {
        "@odata.type": "#microsoft.graph.sitePage",
        "name": name,
        "title": draft.title,
        "pageLayout": "article",
        "canvasLayout": {
            "horizontalSections": [
                {
                    "layout": "oneColumn",
                    "id": "1",
                    "columns": [
                        {
                            "id": "1",
                            "webparts": [
                                {
                                    "@odata.type": "#microsoft.graph.textWebPart",
                                    "innerHtml": render_page_html(draft),
                                }
                            ],
                        }
                    ],
                }
            ]
        },
    }


def render_page_html(draft: DraftPost) -> str:
    """Render an approved ``DraftPost`` into HTML for the Site Page text web part.

    All draft-supplied text is escaped with :func:`html.escape` to prevent markup
    injection into the published page.
    """
    parts: list[str] = [f"<h1>{html.escape(draft.title)}</h1>"]
    parts.append(_section("概要", draft.summary_for_users))
    parts.append(_section("影響", draft.impact))
    parts.append(_list_section("利用者が行う対応", draft.required_actions))
    parts.append(_list_section("管理者が行う対応", draft.admin_actions))
    deadline = draft.deadline.isoformat() if draft.deadline is not None else _DEADLINE_UNSET
    parts.append(_section("対応期限または推奨対応時期", deadline))
    parts.append(_references_section(draft.references))
    return "".join(part for part in parts if part)


def _section(heading: str, body: str) -> str:
    if not body or not body.strip():
        return ""
    return f"<h2>{html.escape(heading)}</h2><p>{html.escape(body)}</p>"


def _list_section(heading: str, items: Sequence[str] | None) -> str:
    if not items:
        return ""
    cleaned = [item for item in items if isinstance(item, str) and item.strip()]
    if not cleaned:
        return ""
    lis = "".join(f"<li>{html.escape(item)}</li>" for item in cleaned)
    return f"<h2>{html.escape(heading)}</h2><ul>{lis}</ul>"


_ALLOWED_URL_SCHEMES = ("https://", "http://")


def _references_section(references: Sequence[Mapping[str, str]]) -> str:
    rendered: list[str] = []
    for ref in references:
        raw_url = str(ref.get("url", ""))
        if not raw_url or not raw_url.startswith(_ALLOWED_URL_SCHEMES):
            continue  # reject javascript:, data:, and relative URLs
        label_val = ref.get("label") or raw_url
        label = html.escape(str(label_val))
        url = html.escape(raw_url)
        rendered.append(f'<li><a href="{url}">{label}</a></li>')
    if not rendered:
        return ""
    return f"<h2>{html.escape('参考情報')}</h2><ul>{''.join(rendered)}</ul>"


def _ascii_slug(value: str) -> str:
    slug = "".join(ch if ch.isascii() and ch.isalnum() else "-" for ch in value.lower())
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or "page"


def _optional_str(raw: Mapping[str, object], key: str) -> str | None:
    value = raw.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


# --- default real transport ------------------------------------------------


def urllib_transport(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: Mapping[str, object] | None,
) -> GraphHttpResponse:
    """Default real transport using stdlib ``urllib`` over HTTPS only.

    Surfaces non-2xx HTTP statuses as a ``GraphHttpResponse`` so the connector can
    classify them; raises ``GraphTransportError`` for network/timeout failures.
    """
    if not url.startswith("https://"):
        raise GraphTransportError("Graph transport requires an https URL")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request_headers = {**dict(headers), "Accept": "application/json"}
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(  # noqa: S310 (https enforced above)
        url, data=data, headers=request_headers, method=method
    )
    try:
        with urllib.request.urlopen(  # noqa: S310 (https enforced above)
            request, timeout=HTTP_TIMEOUT_SECONDS
        ) as response:
            return GraphHttpResponse(
                status=response.status,
                body=_load_json(response.read()),
                headers={key: value for key, value in response.headers.items()},
            )
    except urllib.error.HTTPError as exc:  # surface status for classification
        return GraphHttpResponse(
            status=exc.code,
            body=_load_json(exc.read()),
            headers={key: value for key, value in (exc.headers or {}).items()},
        )
    except (urllib.error.URLError, TimeoutError) as exc:
        raise GraphTransportError(f"Graph transport failed: {exc}") from exc


def _load_json(raw: bytes) -> Mapping[str, object]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, Mapping) else {}


__all__ = [
    "CONNECTOR_VERSION",
    "GRAPH_BASE_URL",
    "ConnectorError",
    "GraphHttpResponse",
    "GraphTransport",
    "GraphTransportError",
    "PublishOutcome",
    "SharePointConnector",
    "TokenProvider",
    "build_idempotency_key",
    "build_site_page_payload",
    "classify_graph_status",
    "render_page_html",
    "urllib_transport",
]
