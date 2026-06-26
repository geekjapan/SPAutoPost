"""delegated PoC の投稿オーケストレーション。

責務:
- idempotency_key の生成（sharepoint-publishing.md の推奨要素）。
- dry-run ゲート（実認証・実投稿を行わず ``dry_run`` Publication と ``publish_dry_run``
  AuditEvent を記録）。
- live 投稿（device code 認証 → Site Page 作成 →（任意 publish）→ ``published`` 記録）。
- 失敗の捕捉（``failed`` Publication と ``error`` AuditEvent を記録し、例外を伝播させない）。
- 投稿者（サインイン user principal）を ``actor``、登録アプリ（client_id）を
  ``service_principal`` として AuditEvent に記録する。

Config には依存せず、必要なスカラだけを受け取る（呼び出し側が env 参照を解決する）。
"""

from __future__ import annotations

import hashlib
import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime

from ..llm import ProviderMetadata
from ..review_workflow import assert_publishable
from ..storage.models import (
    AuditEvent,
    AuditEventType,
    DraftStatus,
    Publication,
    PublicationOperation,
    TargetType,
)
from ..storage.port import StoragePort
from .auth import GraphTokenProvider
from .errors import GraphApiError, GraphAuthError
from .sharepoint_client import SharePointPagesClient, build_create_page_request

IdFactory = Callable[[], str]

# 既に投稿済み/投稿中なら新規 Graph 作成をしない（重複投稿防止）。
_IDEMPOTENT_STATUSES: tuple[str, ...] = ("published", "publishing")
_PUBLISH_FAILED = "publish_failed"
_TARGET_TYPE: TargetType = "site-page"


@dataclass(frozen=True)
class PublishResult:
    """publish 1 回の結果（Publication・記録した AuditEvent・dry-run か・新規作成したか）。"""

    publication: Publication
    audit_events: tuple[AuditEvent, ...]
    dry_run: bool
    created: bool


def _default_id_factory() -> str:
    return uuid.uuid4().hex


def normalize_title(title: str) -> str:
    """idempotency_key 用に title を正規化する（前後空白除去・連続空白圧縮・小文字化）。"""
    return re.sub(r"\s+", " ", title.strip()).lower()


def build_idempotency_key(
    *,
    draft_id: str,
    target_site_id: str | None,
    target_page_library_id: str | None,
    advisory_ids: Sequence[str],
    title: str,
) -> str:
    """draft・投稿先・advisory・正規化 title から決定論的な idempotency_key を作る。"""
    parts = [
        draft_id or "",
        target_site_id or "",
        target_page_library_id or "",
        "|".join(sorted(advisory_ids)),
        normalize_title(title),
    ]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _failure_details(exc: Exception) -> tuple[str, bool]:
    """例外を (error_code, retryable) に対応づける（sharepoint-publishing.md の error code）。"""
    if isinstance(exc, GraphAuthError):
        return "authentication_failed", False
    if isinstance(exc, GraphApiError):
        if exc.status_code in (401, 403):
            return "authorization_failed", False
        if exc.status_code == 429:
            return "graph_rate_limited", True
        return "graph_api_error", exc.retryable
    return _PUBLISH_FAILED, False


def _build_publication(
    *,
    publication_id: str,
    draft_id: str,
    idempotency_key: str,
    target_site_id: str,
    target_page_library_id: str | None,
    status: str,
    operation: PublicationOperation,
    now: datetime,
    sharepoint_page_id: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    retryable: bool | None = None,
) -> Publication:
    return Publication(
        publication_id=publication_id,
        draft_id=draft_id,
        target_type=_TARGET_TYPE,
        target_site_id=target_site_id,
        publication_status=status,  # type: ignore[arg-type]
        idempotency_key=idempotency_key,
        created_at=now,
        updated_at=now,
        target_page_library_id=target_page_library_id,
        sharepoint_page_id=sharepoint_page_id,
        operation=operation,
        published_at=now if status == "published" else None,
        error_code=error_code,
        error_message=error_message,
        retryable=retryable,
    )


def _build_audit(
    *,
    event_type: AuditEventType,
    result: str,
    correlation_id: str,
    audit_event_id: str,
    now: datetime,
    operation: PublicationOperation,
    target_site_id: str | None,
    target_page_library_id: str | None,
    actor: str | None = None,
    service_principal: str | None = None,
    sharepoint_page_id: str | None = None,
    provider: ProviderMetadata | None = None,
    advisory_id: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> AuditEvent:
    related_ids: dict[str, object] = {}
    if advisory_id is not None:
        related_ids["advisory_id"] = advisory_id
    return AuditEvent(
        audit_event_id=audit_event_id,
        event_type=event_type,
        correlation_id=correlation_id,
        result=result,  # type: ignore[arg-type]
        created_at=now,
        actor=actor,
        service_principal=service_principal,
        provider_name=provider.provider_name if provider else None,
        provider_type=provider.provider_type if provider else None,
        prompt_version=provider.prompt_version if provider else None,
        target_site_id=target_site_id,
        target_page_library_id=target_page_library_id,
        sharepoint_page_id=sharepoint_page_id,
        idempotency_key=None,
        operation=operation,
        error_code=error_code,
        error_message=error_message,
        related_ids=related_ids or None,
    )


def publish_site_page(
    page_payload: dict[str, object],
    *,
    dry_run: bool,
    store: StoragePort,
    now: datetime,
    draft_id: str,
    draft_status: DraftStatus,
    title: str,
    target_site_id: str,
    target_page_library_id: str | None = None,
    advisory_ids: Sequence[str] = (),
    advisory_id: str | None = None,
    provider: ProviderMetadata | None = None,
    client_id: str | None = None,
    token_provider: GraphTokenProvider | None = None,
    client: SharePointPagesClient | None = None,
    promote: bool = False,
    id_factory: IdFactory = _default_id_factory,
) -> PublishResult:
    """Site Page を dry-run または live で投稿し、Publication / AuditEvent を記録する。

    ``page_payload`` は :func:`spautopost.dry_run.build_site_page_payload` の出力。
    live（``dry_run=False``）では ``token_provider`` と ``client`` が必須。失敗は捕捉して
    ``failed`` Publication と ``error`` AuditEvent に記録し、例外は伝播させない。
    """
    assert_publishable(draft_id=draft_id, draft_status=draft_status)

    correlation_id = id_factory()
    key = build_idempotency_key(
        draft_id=draft_id,
        target_site_id=target_site_id,
        target_page_library_id=target_page_library_id,
        advisory_ids=advisory_ids,
        title=title,
    )
    existing = store.publications.get_by_idempotency_key(key)
    if existing is not None and existing.publication_status in _IDEMPOTENT_STATUSES and not dry_run:
        # 重複投稿防止: 既に published/publishing の Publication があれば新規作成しない。
        return PublishResult(publication=existing, audit_events=(), dry_run=False, created=False)

    publication_id = existing.publication_id if existing is not None else id_factory()

    if dry_run:
        publication = _build_publication(
            publication_id=publication_id,
            draft_id=draft_id,
            idempotency_key=key,
            target_site_id=target_site_id,
            target_page_library_id=target_page_library_id,
            status="dry_run",
            operation="dry-run",
            now=now,
        )
        audit = _build_audit(
            event_type="publish_dry_run",
            result="success",
            correlation_id=correlation_id,
            audit_event_id=id_factory(),
            now=now,
            operation="dry-run",
            target_site_id=target_site_id,
            target_page_library_id=target_page_library_id,
            provider=provider,
            advisory_id=advisory_id,
        )
        stored = store.publications.upsert(publication)
        store.audit_events.append(audit)
        return PublishResult(publication=stored, audit_events=(audit,), dry_run=True, created=False)

    if token_provider is None or client is None:
        raise GraphAuthError("live publish requires a token_provider and a pages client")

    # リトライ: 既存 failed Publication に sharepoint_page_id があれば UPDATE 経路を選ぶ。
    # update_page_id が非 None のとき UPDATE 経路、None のとき CREATE 経路。
    update_page_id: str | None = (
        existing.sharepoint_page_id
        if existing is not None
        and existing.publication_status == "failed"
        and existing.sharepoint_page_id is not None
        else None
    )
    initial_page_id: str | None = existing.sharepoint_page_id if existing is not None else None

    # pending 状態を記録してから Graph 呼び出しに進む（状態追跡）。
    pending_pub = _build_publication(
        publication_id=publication_id,
        draft_id=draft_id,
        idempotency_key=key,
        target_site_id=target_site_id,
        target_page_library_id=target_page_library_id,
        status="pending",
        operation="update" if update_page_id is not None else "create",
        now=now,
        sharepoint_page_id=initial_page_id,
    )
    store.publications.upsert(pending_pub)

    created_page_id: str | None = initial_page_id
    try:
        auth = token_provider.acquire()
        request_body = build_create_page_request(page_payload)

        # token 取得後・API 呼び出し前に publishing 状態へ遷移する。
        publishing_pub = _build_publication(
            publication_id=publication_id,
            draft_id=draft_id,
            idempotency_key=key,
            target_site_id=target_site_id,
            target_page_library_id=target_page_library_id,
            status="publishing",
            operation="update" if update_page_id is not None else "create",
            now=now,
            sharepoint_page_id=initial_page_id,
        )
        store.publications.upsert(publishing_pub)

        actor = auth.identity.user_principal_name

        if update_page_id is not None:
            # リトライ: 既存ページをコンテンツ更新する。
            client.update_site_page(
                site_id=target_site_id,
                page_id=update_page_id,
                request_body=request_body,
                access_token=auth.access_token,
            )
            operation: PublicationOperation = "update"
            final_page_id = update_page_id
            audits = [
                _build_audit(
                    event_type="publish_update",
                    result="success",
                    correlation_id=correlation_id,
                    audit_event_id=id_factory(),
                    now=now,
                    operation=operation,
                    target_site_id=target_site_id,
                    target_page_library_id=target_page_library_id,
                    actor=actor,
                    service_principal=client_id,
                    sharepoint_page_id=final_page_id,
                    provider=provider,
                    advisory_id=advisory_id,
                )
            ]
            if promote:
                client.publish_site_page(
                    site_id=target_site_id,
                    page_id=update_page_id,
                    access_token=auth.access_token,
                )
                operation = "publish"
                audits.append(
                    _build_audit(
                        event_type="publish_result",
                        result="success",
                        correlation_id=correlation_id,
                        audit_event_id=id_factory(),
                        now=now,
                        operation="publish",
                        target_site_id=target_site_id,
                        target_page_library_id=target_page_library_id,
                        actor=actor,
                        service_principal=client_id,
                        sharepoint_page_id=update_page_id,
                        provider=provider,
                        advisory_id=advisory_id,
                    )
                )
        else:
            created_page = client.create_site_page(
                site_id=target_site_id,
                request_body=request_body,
                access_token=auth.access_token,
            )
            created_page_id = created_page.page_id
            operation = "create"
            final_page_id = created_page.page_id
            audits = [
                _build_audit(
                    event_type="publish_create",
                    result="success",
                    correlation_id=correlation_id,
                    audit_event_id=id_factory(),
                    now=now,
                    operation=operation,
                    target_site_id=target_site_id,
                    target_page_library_id=target_page_library_id,
                    actor=actor,
                    service_principal=client_id,
                    sharepoint_page_id=final_page_id,
                    provider=provider,
                    advisory_id=advisory_id,
                )
            ]
            if promote:
                client.publish_site_page(
                    site_id=target_site_id,
                    page_id=created_page.page_id,
                    access_token=auth.access_token,
                )
                operation = "publish"
                audits.append(
                    _build_audit(
                        event_type="publish_result",
                        result="success",
                        correlation_id=correlation_id,
                        audit_event_id=id_factory(),
                        now=now,
                        operation="publish",
                        target_site_id=target_site_id,
                        target_page_library_id=target_page_library_id,
                        actor=actor,
                        service_principal=client_id,
                        sharepoint_page_id=created_page.page_id,
                        provider=provider,
                        advisory_id=advisory_id,
                    )
                )

        publication = _build_publication(
            publication_id=publication_id,
            draft_id=draft_id,
            idempotency_key=key,
            target_site_id=target_site_id,
            target_page_library_id=target_page_library_id,
            status="published",
            operation=operation,
            now=now,
            sharepoint_page_id=final_page_id,
        )
        stored = store.publications.upsert(publication)
        for audit in audits:
            store.audit_events.append(audit)
        return PublishResult(
            publication=stored,
            audit_events=tuple(audits),
            dry_run=False,
            created=update_page_id is None,
        )
    except Exception as exc:  # noqa: BLE001 - 投稿失敗は failed として記録し伝播させない
        error_code, retryable = _failure_details(exc)
        # 既知エラー型のみ str(exc) を使い、未知例外はメッセージを汚染しない（LOW #4）。
        from .errors import GraphError

        error_message = str(exc) if isinstance(exc, GraphError) else "unexpected publish error"
        failed_operation: PublicationOperation = (
            "update" if update_page_id is not None else "create"
        )
        publication = _build_publication(
            publication_id=publication_id,
            draft_id=draft_id,
            idempotency_key=key,
            target_site_id=target_site_id,
            target_page_library_id=target_page_library_id,
            status="failed",
            operation=failed_operation,
            now=now,
            sharepoint_page_id=created_page_id,
            error_code=error_code,
            error_message=error_message,
            retryable=retryable,
        )
        audit = _build_audit(
            event_type="error",
            result="failure",
            correlation_id=correlation_id,
            audit_event_id=id_factory(),
            now=now,
            operation=failed_operation,
            target_site_id=target_site_id,
            target_page_library_id=target_page_library_id,
            sharepoint_page_id=created_page_id,
            service_principal=client_id,
            provider=provider,
            advisory_id=advisory_id,
            error_code=error_code,
            error_message=error_message,
        )
        # failure 記録中の StorageError は best-effort で吸収する（MEDIUM #2）。
        try:
            stored = store.publications.upsert(publication)
            store.audit_events.append(audit)
        except Exception:  # noqa: BLE001
            stored = publication
        return PublishResult(
            publication=stored,
            audit_events=(audit,),
            dry_run=False,
            created=created_page_id is not None,
        )
