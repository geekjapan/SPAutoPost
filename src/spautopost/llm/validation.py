"""DraftOutput の構造・安全性・出典根拠を検証する純粋関数モジュール。"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from . import DraftOutput

IssueSeverity = Literal["error", "warning", "info"]

# 攻撃手順・PoC を示す検出パターン（英語・日本語）
# re.ASCII により \b はASCII文字のみを基準に動作し、日本語に隣接する英語パターンを
# 正しく検出しつつ "epoch"/"pocket" などへの誤検出を防ぐ
_DANGEROUS_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE | re.ASCII)
    for p in [
        r"\bexploit\s+code\b",
        r"\bproof\s+of\s+concept\b",
        r"\bpoc\b",
        r"\battack\s+steps?\b",
        r"\bpayload\b",
        r"\breverse\s+shell\b",
        r"\bshellcode\b",
        r"攻撃手順",
        r"悪用コード",
        r"exploit\s*コード",
    ]
)


@dataclass(frozen=True)
class ValidationIssue:
    """検証で発行される単一の問題。"""

    severity: IssueSeverity
    code: str
    message: str
    reviewer_hint: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """validate_draft_output の返り値。"""

    issues: Sequence[ValidationIssue] = field(default_factory=tuple)
    regeneration_hints: Sequence[str] = field(default_factory=tuple)
    reviewer_warnings: Sequence[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "issues", tuple(self.issues))
        object.__setattr__(self, "regeneration_hints", tuple(self.regeneration_hints))
        object.__setattr__(self, "reviewer_warnings", tuple(self.reviewer_warnings))

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == "warning" for i in self.issues)


def validate_draft_output(draft: DraftOutput) -> ValidationResult:
    """DraftOutput の構造・安全性・出典根拠を検証し ValidationResult を返す。"""
    issues: list[ValidationIssue] = []
    issues.extend(_check_required_sections(draft))
    issues.extend(_check_references(draft))
    issues.extend(_check_unsupported_claims(draft))
    issues.extend(_check_dangerous_details(draft))
    issues.extend(_check_uncertainty_notes(draft))

    regeneration_hints = tuple(i.message for i in issues if i.severity == "error")
    reviewer_warnings = tuple(i.reviewer_hint for i in issues if i.reviewer_hint is not None)

    return ValidationResult(
        issues=tuple(issues),
        regeneration_hints=regeneration_hints,
        reviewer_warnings=reviewer_warnings,
    )


# ---------------------------------------------------------------------------
# チェックヘルパー（各 1 つの責務）
# ---------------------------------------------------------------------------


def _check_required_sections(draft: DraftOutput) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    required_str_fields = [
        ("title", draft.title),
        ("summary_for_users", draft.summary_for_users),
        ("impact", draft.impact),
    ]
    for name, value in required_str_fields:
        if not isinstance(value, str) or not value.strip():
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="missing_required_section",
                    message=f"必須フィールド '{name}' が空です。再生成してください。",
                )
            )

    # 空文字列のみのシーケンスも「空」として扱う
    actions = draft.required_actions or ()
    has_valid_action = any(isinstance(a, str) and a.strip() for a in actions)
    if not has_valid_action:
        issues.append(
            ValidationIssue(
                severity="error",
                code="missing_required_section",
                message="必須フィールド 'required_actions' が空です。再生成してください。",
            )
        )

    return issues


def _check_references(draft: DraftOutput) -> list[ValidationIssue]:
    refs = draft.references or ()
    has_valid_url = any(
        isinstance(r, dict) and isinstance(r.get("url"), str) and r["url"].strip() for r in refs
    )
    if has_valid_url:
        return []
    return [
        ValidationIssue(
            severity="warning",
            code="no_references",
            message="出典情報が含まれていません。",
            reviewer_hint="出典情報を確認し、適切な参考 URL または advisory を追加してください。",
        )
    ]


def _check_unsupported_claims(draft: DraftOutput) -> list[ValidationIssue]:
    validation_hints = draft.validation_hints or ()
    has_guardrail = "guardrail:no_unsupported_claims" in validation_hints
    has_warnings = bool(draft.warnings)
    if has_guardrail or has_warnings:
        return []
    return [
        ValidationIssue(
            severity="warning",
            code="unsupported_claim_risk",
            message="出典根拠チェック guardrail が設定されていません。",
            reviewer_hint="出典にない断定が含まれていないか確認してください。",
        )
    ]


def _check_dangerous_details(draft: DraftOutput) -> list[ValidationIssue]:
    texts = _collect_text_fields(draft)
    for text in texts:
        for pattern in _DANGEROUS_PATTERNS:
            if pattern.search(text):
                return [
                    ValidationIssue(
                        severity="error",
                        code="dangerous_detail_detected",
                        message="攻撃手順・PoC・exploit 詳細を示すパターンが検出されました。",
                        reviewer_hint="該当箇所を削除または一般的な表現に差し替えてください。",
                    )
                ]
    return []


def _check_uncertainty_notes(draft: DraftOutput) -> list[ValidationIssue]:
    if draft.uncertainty_notes:
        return []
    return [
        ValidationIssue(
            severity="info",
            code="no_uncertainty_notes",
            message="不確実性に関する注記がありません。",
            reviewer_hint="不明な情報（期限・対象製品・patch 状況）がないか確認してください。",
        )
    ]


def _collect_text_fields(draft: DraftOutput) -> list[str]:
    """検査対象の文字列フィールドを収集する。"""
    texts: list[str] = []
    for value in (draft.title, draft.summary_for_users, draft.impact):
        if isinstance(value, str):
            texts.append(value)
    for seq in (draft.required_actions, draft.admin_actions):
        if seq:
            for item in seq:
                if isinstance(item, str):
                    texts.append(item)
    return texts


__all__ = [
    "ValidationIssue",
    "ValidationResult",
    "validate_draft_output",
]
