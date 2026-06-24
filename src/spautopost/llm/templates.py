"""SharePoint announcements 向けの draft composition template。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import AdvisoryPayload, DraftInput, DraftOutput, Urgency

SHAREPOINT_ANNOUNCEMENT_TEMPLATE_ID = "sharepoint-announcement-m1"
SHAREPOINT_ANNOUNCEMENT_PROMPT_TEMPLATE = """\
Role: 社内セキュリティ担当者として、SharePoint お知らせ掲示板向け原稿を作成する。
Input: Advisory, references, urgency, audience.
Output: DraftOutput(title, summary_for_users, impact, required_actions,
        admin_actions, deadline, references).
Safety: PoC、攻撃手順、攻撃コードを説明しない。
Grounding: 出典にない内容を断定しない。不明点は reviewer warning に残す。
"""

_GUARDRAIL_HINTS = (
    "guardrail:no_unsupported_claims",
    "guardrail:no_attack_steps_or_poc",
    "human_review_required",
)


def compose_sharepoint_draft(
    draft_input: DraftInput, *, generation_input_hash: str | None = None
) -> DraftOutput:
    """Advisory から SharePoint announcements 向け DraftOutput を組み立てる。"""
    from . import DraftOutput

    advisory = _first_advisory(draft_input.advisory)
    title = _text(advisory, "title", "セキュリティ注意喚起")
    summary = _text(advisory, "summary", "公開情報に基づく確認が必要です。")
    products = _list_text(advisory.get("affected_products"))
    deadline = _deadline(advisory)
    uncertainty_notes = _uncertainty_notes(advisory, deadline)

    return DraftOutput(
        title=f"{_urgency_prefix(draft_input.urgency)} {title} 対応について",
        summary_for_users=(
            f"{summary} 不審な動作や影響が疑われる場合は、社内窓口へ連絡してください。"
        ),
        impact=_impact(summary, products),
        required_actions=_required_actions(advisory, deadline),
        admin_actions=_admin_actions(advisory, products),
        deadline=deadline,
        references=tuple(draft_input.references),
        warnings=("出典にない断定を避け、必要に応じて reviewer が補足してください。",),
        uncertainty_notes=uncertainty_notes,
        source_mapping={
            "template_id": SHAREPOINT_ANNOUNCEMENT_TEMPLATE_ID,
            "prompt_version": draft_input.prompt_version,
        },
        validation_hints=_GUARDRAIL_HINTS,
        generation_input_hash=generation_input_hash,
    )


def _first_advisory(advisory: AdvisoryPayload | Sequence[AdvisoryPayload]) -> Mapping[str, object]:
    if isinstance(advisory, Mapping):
        return advisory
    if isinstance(advisory, Sequence) and not isinstance(advisory, str | bytes | bytearray):
        first = next(iter(advisory), None)
        if isinstance(first, Mapping):
            return first
    return {}


def _text(advisory: Mapping[str, object], key: str, default: str) -> str:
    value = advisory.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else default


def _list_text(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        return ()
    items: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            items.append(item.strip())
        elif isinstance(item, Mapping):
            product = item.get("product") or item.get("name")
            if isinstance(product, str) and product.strip():
                items.append(product.strip())
    return tuple(items)


def _deadline(advisory: Mapping[str, object]) -> str | None:
    for key in ("deadline", "due_date", "recommended_deadline"):
        value = advisory.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _impact(summary: str, products: Sequence[str]) -> str:
    if products:
        return f"対象候補: {', '.join(products)}。影響は出典に記載された範囲で確認してください。"
    return f"{summary} 対象製品や影響範囲は出典で確認してください。"


def _required_actions(advisory: Mapping[str, object], deadline: str | None) -> tuple[str, ...]:
    actions = ["利用中の対象製品またはサービスがあるか確認してください。"]
    workaround = _text(advisory, "workaround", "")
    if workaround:
        actions.append(f"出典に記載された回避策を確認してください: {workaround}")
    actions.append("更新プログラムまたは公式の対応手順が案内されている場合は適用してください。")
    if deadline:
        actions.append(f"推奨対応時期: {deadline}")
    return tuple(actions)


def _admin_actions(advisory: Mapping[str, object], products: Sequence[str]) -> tuple[str, ...]:
    scope = ", ".join(products) if products else "対象製品"
    actions = [
        f"管理対象環境で {scope} の利用有無と適用状況を確認してください。",
        "公式出典を確認し、必要な更新、回避策、利用者案内を実施してください。",
    ]
    patch_available = advisory.get("patch_available")
    if patch_available == "unknown" or patch_available is None:
        actions.append("patch availability が不明な場合は reviewer warning として扱ってください。")
    return tuple(actions)


def _uncertainty_notes(advisory: Mapping[str, object], deadline: str | None) -> tuple[str, ...]:
    notes: list[str] = []
    if not _list_text(advisory.get("affected_products")):
        notes.append("対象製品が不明です。")
    if deadline is None:
        notes.append("対応期限が不明です。")
    if advisory.get("patch_available") in (None, "unknown"):
        notes.append("patch availability が不明です。")
    if advisory.get("exploit_status") in (None, "unknown"):
        notes.append("exploit status が不明です。")
    return tuple(notes)


def _urgency_prefix(urgency: Urgency) -> str:
    return {
        "emergency": "[緊急]",
        "high": "[重要]",
        "normal": "[注意喚起]",
        "low": "[参考]",
    }.get(urgency, "[注意喚起]")


__all__ = [
    "SHAREPOINT_ANNOUNCEMENT_PROMPT_TEMPLATE",
    "SHAREPOINT_ANNOUNCEMENT_TEMPLATE_ID",
    "compose_sharepoint_draft",
]
