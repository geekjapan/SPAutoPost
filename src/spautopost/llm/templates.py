"""SharePoint announcements 向けの draft composition template。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
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
    input_hash = generation_input_hash or _input_hash(draft_input)
    template_id = draft_input.template_id.strip() or SHAREPOINT_ANNOUNCEMENT_TEMPLATE_ID

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
            "template_id": template_id,
            "prompt_version": draft_input.prompt_version,
        },
        validation_hints=_GUARDRAIL_HINTS,
        generation_input_hash=input_hash,
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
    return tuple(dict.fromkeys(items))


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
    for guidance in _action_guidance(advisory):
        actions.append(f"出典に記載された対応方法を確認してください: {guidance}")
    actions.append("更新プログラムまたは公式の対応手順が案内されている場合は適用してください。")
    if deadline:
        actions.append(f"推奨対応時期: {deadline}")
    return tuple(actions)


def _action_guidance(advisory: Mapping[str, object]) -> tuple[str, ...]:
    items = [
        text
        for key in ("workaround", "mitigation", "solution", "remediation")
        if (text := _text(advisory, key, ""))
    ]
    return tuple(dict.fromkeys(items))


def _admin_actions(advisory: Mapping[str, object], products: Sequence[str]) -> tuple[str, ...]:
    scope = ", ".join(products) if products else "対象製品"
    actions = [
        f"管理対象環境で {scope} の利用有無と適用状況を確認してください。",
        "公式出典を確認し、必要な更新、回避策、利用者案内を実施してください。",
    ]
    patch_available = advisory.get("patch_available")
    if isinstance(patch_available, str):
        patch_available = patch_available.strip().lower()
    if patch_available == "unknown" or patch_available is None:
        actions.append("patch availability が不明な場合は reviewer warning として扱ってください。")
    return tuple(actions)


def _uncertainty_notes(advisory: Mapping[str, object], deadline: str | None) -> tuple[str, ...]:
    notes: list[str] = []
    if not _list_text(advisory.get("affected_products")):
        notes.append("対象製品が不明です。")
    if deadline is None:
        notes.append("対応期限が不明です。")
    patch_available = advisory.get("patch_available")
    if isinstance(patch_available, str):
        patch_available = patch_available.strip().lower()
    if patch_available in (None, "unknown"):
        notes.append("patch availability が不明です。")
    exploit_status = advisory.get("exploit_status")
    if isinstance(exploit_status, str):
        exploit_status = exploit_status.strip().lower()
    if exploit_status in (None, "unknown"):
        notes.append("exploit status が不明です。")
    return tuple(notes)


def _urgency_prefix(urgency: Urgency) -> str:
    return {
        "emergency": "[緊急]",
        "high": "[重要]",
        "normal": "[注意喚起]",
        "low": "[参考]",
    }.get(urgency, "[注意喚起]")


def _input_hash(draft_input: DraftInput) -> str:
    payload = _stable_value(draft_input)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _stable_value(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return _stable_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _stable_value(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_stable_value(item) for item in value]
    return value


__all__ = [
    "SHAREPOINT_ANNOUNCEMENT_PROMPT_TEMPLATE",
    "SHAREPOINT_ANNOUNCEMENT_TEMPLATE_ID",
    "compose_sharepoint_draft",
]
