"""dry-run preview と最小監査ログの組み立て。

実投稿・外部 API 呼び出し・Secret 解決は行わない。投稿先識別子は ``env:`` 参照のまま
扱い、出力境界（CLI）で :func:`spautopost.secrets.redact_config` により秘匿する。

設計の正本: docs/specs/draft-composition.md（Site Page 必須セクション）、
docs/specs/audit-log.md（AuditEvent / event_type / 失敗時記録）、Issue #10。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import datetime
from typing import Any

from .llm import DraftOutput, ProviderMetadata
from .storage.models import AuditEvent, Urgency

# draft-composition.md の必須セクション順。Site Page payload はこの構成で組み立てる。
REQUIRED_SECTION_HEADINGS: tuple[str, ...] = (
    "概要",
    "影響",
    "対象",
    "利用者が行う対応",
    "管理者が行う対応",
    "対応期限または推奨対応時期",
    "参考情報",
)

# DraftOutput には「対象（影響を受ける製品）」専用フィールドが無い。reviewer が advisory
# から補う前提で placeholder を出す。将来 DraftOutput に対象 field が追加されたら置き換える。
TARGET_SECTION_PLACEHOLDER = "（対象製品は advisory を参照して確認してください）"
DEADLINE_UNSET = "未定（要確認）"

GENERATION_FAILED = "draft_generation_failed"


def build_site_page_payload(
    draft: DraftOutput,
    *,
    urgency: Urgency,
    target_site_id: str | None,
    target_page_library_id: str | None,
    mode: str = "site-page",
) -> dict[str, Any]:
    """生成済み ``DraftOutput`` から SharePoint Site Page 投稿予定 payload を組み立てる。

    返す dict は JSON 直列化可能。``target_*`` は ``env:`` 参照のまま入る場合があるため、
    出力時に呼び出し側で redaction すること。
    """
    references = [dict(ref) for ref in draft.references]
    sections: list[dict[str, Any]] = [
        {"heading": "概要", "body": draft.summary_for_users},
        {"heading": "影響", "body": draft.impact},
        {"heading": "対象", "body": TARGET_SECTION_PLACEHOLDER},
        {"heading": "利用者が行う対応", "items": list(draft.required_actions)},
        {"heading": "管理者が行う対応", "items": list(draft.admin_actions)},
        {"heading": "対応期限または推奨対応時期", "body": draft.deadline or DEADLINE_UNSET},
        {"heading": "参考情報", "references": references},
    ]
    return {
        "mode": mode,
        "urgency": urgency,
        "target": {
            "site_id": target_site_id,
            "page_library_id": target_page_library_id,
        },
        "title": draft.title,
        "sections": sections,
        # reviewer が必ず確認すべき非確定情報。本文へは混ぜない（draft-composition.md）。
        "review_warnings": [*draft.warnings, *draft.uncertainty_notes],
    }


def build_preview_audit_event(
    *,
    provider: ProviderMetadata,
    draft: DraftOutput,
    correlation_id: str,
    audit_event_id: str,
    now: datetime,
    advisory_id: str | None = None,
    target_site_id: str | None = None,
    target_page_library_id: str | None = None,
) -> AuditEvent:
    """dry-run 成功イベント（``publish_dry_run`` / ``success``）を組み立てる。

    generation_input_hash は AuditEvent 専用フィールドが無いため ``related_ids`` に格納する。
    """
    related_ids: dict[str, object] = {}
    if advisory_id is not None:
        related_ids["advisory_id"] = advisory_id
    if draft.generation_input_hash is not None:
        related_ids["generation_input_hash"] = draft.generation_input_hash
    return AuditEvent(
        audit_event_id=audit_event_id,
        event_type="publish_dry_run",
        correlation_id=correlation_id,
        result="success",
        created_at=now,
        provider_name=provider.provider_name,
        provider_type=provider.provider_type,
        prompt_version=provider.prompt_version,
        target_site_id=target_site_id,
        target_page_library_id=target_page_library_id,
        operation="dry-run",
        related_ids=related_ids or None,
    )


def build_error_audit_event(
    *,
    correlation_id: str,
    audit_event_id: str,
    now: datetime,
    error_code: str,
    error_message: str,
    provider: ProviderMetadata | None = None,
) -> AuditEvent:
    """dry-run 失敗イベント（``error`` / ``failure``）を組み立てる。

    error_message には Secret / token を含めないこと（呼び出し側の責務）。
    """
    return AuditEvent(
        audit_event_id=audit_event_id,
        event_type="error",
        correlation_id=correlation_id,
        result="failure",
        created_at=now,
        provider_name=provider.provider_name if provider else None,
        provider_type=provider.provider_type if provider else None,
        prompt_version=provider.prompt_version if provider else None,
        operation="dry-run",
        error_code=error_code,
        error_message=error_message,
    )


def audit_event_to_dict(event: AuditEvent) -> dict[str, Any]:
    """AuditEvent を JSON 直列化可能な dict に変換する（None フィールドは省く）。"""
    raw = asdict(event)
    return {key: _json_ready(value) for key, value in raw.items() if value is not None}


def _json_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_json_ready(item) for item in value]
    return value


__all__ = [
    "GENERATION_FAILED",
    "REQUIRED_SECTION_HEADINGS",
    "audit_event_to_dict",
    "build_error_audit_event",
    "build_preview_audit_event",
    "build_site_page_payload",
]
