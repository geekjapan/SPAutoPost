"""AI 出力検証モジュールの単体テスト（TDD）。"""

from __future__ import annotations

import pytest

from spautopost.llm import DraftOutput, ValidationIssue, ValidationResult, validate_draft_output

# ---------------------------------------------------------------------------
# テストヘルパー
# ---------------------------------------------------------------------------


def _make_draft(**overrides: object) -> DraftOutput:
    """最低限有効な DraftOutput を生成する。"""
    defaults: dict[str, object] = {
        "title": "重要: Example の脆弱性対応について",
        "summary_for_users": "出典に基づく確認が必要です。社内窓口へ連絡してください。",
        "impact": "対象候補: Example Product。出典で確認してください。",
        "required_actions": ("対象製品の利用有無を確認してください。",),
        "references": ({"title": "Vendor advisory", "url": "https://example.test/adv"},),
        "warnings": ("出典にない断定を避けてください。",),
        "uncertainty_notes": ("patch availability が不明です。",),
        "validation_hints": (
            "guardrail:no_unsupported_claims",
            "guardrail:no_attack_steps_or_poc",
            "human_review_required",
        ),
    }
    defaults.update(overrides)
    return DraftOutput(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 型テスト
# ---------------------------------------------------------------------------


def test_validation_issue_is_frozen_dataclass() -> None:
    issue = ValidationIssue(severity="error", code="test_code", message="test message")
    assert issue.severity == "error"
    assert issue.code == "test_code"
    assert issue.message == "test message"
    assert issue.reviewer_hint is None

    with pytest.raises((AttributeError, TypeError)):
        issue.severity = "warning"  # type: ignore[misc]


def test_validation_result_has_errors_true_when_error_issues_present() -> None:
    issue = ValidationIssue(severity="error", code="c1", message="m1")
    result = ValidationResult(issues=(issue,))
    assert result.has_errors is True


def test_validation_result_has_errors_false_when_only_warnings() -> None:
    draft = _make_draft(references=())
    result = validate_draft_output(draft)
    assert result.has_errors is False


def test_validation_result_has_warnings_true_when_warning_issues() -> None:
    draft = _make_draft(references=())
    result = validate_draft_output(draft)
    assert result.has_warnings is True


def test_validation_result_has_warnings_false_when_no_warning_issues() -> None:
    draft = _make_draft()
    result = validate_draft_output(draft)
    assert result.has_warnings is False


def test_validation_result_sequences_are_always_tuples() -> None:
    """リストを渡しても __post_init__ が tuple に強制変換することを確認する。"""
    issue = ValidationIssue(severity="error", code="c1", message="m1")
    result = ValidationResult(
        issues=[issue],
        regeneration_hints=["hint"],
        reviewer_warnings=["w"],
    )
    assert isinstance(result.issues, tuple)
    assert isinstance(result.regeneration_hints, tuple)
    assert isinstance(result.reviewer_warnings, tuple)


# ---------------------------------------------------------------------------
# required sections check
# ---------------------------------------------------------------------------


def test_required_sections_all_present_no_error() -> None:
    result = validate_draft_output(_make_draft())
    codes = {i.code for i in result.issues}
    assert "missing_required_section" not in codes


def test_required_sections_empty_title_raises_error() -> None:
    result = validate_draft_output(_make_draft(title=""))
    errors = [
        i for i in result.issues if i.code == "missing_required_section" and i.severity == "error"
    ]
    assert errors, "title が空のとき missing_required_section エラーが発行されること"


def test_required_sections_whitespace_only_title_raises_error() -> None:
    result = validate_draft_output(_make_draft(title="   "))
    errors = [
        i for i in result.issues if i.code == "missing_required_section" and i.severity == "error"
    ]
    assert errors


def test_required_sections_empty_summary_raises_error() -> None:
    result = validate_draft_output(_make_draft(summary_for_users=""))
    errors = [
        i for i in result.issues if i.code == "missing_required_section" and i.severity == "error"
    ]
    assert errors


def test_required_sections_empty_impact_raises_error() -> None:
    result = validate_draft_output(_make_draft(impact=""))
    errors = [
        i for i in result.issues if i.code == "missing_required_section" and i.severity == "error"
    ]
    assert errors


def test_required_sections_empty_required_actions_raises_error() -> None:
    result = validate_draft_output(_make_draft(required_actions=()))
    errors = [
        i for i in result.issues if i.code == "missing_required_section" and i.severity == "error"
    ]
    assert errors


def test_required_sections_blank_only_required_actions_raises_error() -> None:
    result = validate_draft_output(_make_draft(required_actions=("",)))
    errors = [
        i for i in result.issues if i.code == "missing_required_section" and i.severity == "error"
    ]
    assert errors, "空文字列のみの required_actions はエラーを発行すること"


def test_required_sections_whitespace_only_required_actions_raises_error() -> None:
    result = validate_draft_output(_make_draft(required_actions=("   ",)))
    errors = [
        i for i in result.issues if i.code == "missing_required_section" and i.severity == "error"
    ]
    assert errors, "空白のみの required_actions はエラーを発行すること"


# ---------------------------------------------------------------------------
# references check
# ---------------------------------------------------------------------------


def test_references_present_no_warning() -> None:
    result = validate_draft_output(_make_draft())
    codes = {i.code for i in result.issues}
    assert "no_references" not in codes


def test_references_empty_emits_warning() -> None:
    result = validate_draft_output(_make_draft(references=()))
    warnings = [i for i in result.issues if i.code == "no_references" and i.severity == "warning"]
    assert warnings
    assert warnings[0].reviewer_hint is not None


def test_references_without_url_emits_warning() -> None:
    result = validate_draft_output(_make_draft(references=({"label": "vendor"},)))
    warnings = [i for i in result.issues if i.code == "no_references" and i.severity == "warning"]
    assert warnings, "URL を持たない reference は no_references 警告を発行すること"


def test_references_with_blank_url_emits_warning() -> None:
    result = validate_draft_output(_make_draft(references=({"label": "vendor", "url": ""},)))
    warnings = [i for i in result.issues if i.code == "no_references" and i.severity == "warning"]
    assert warnings, "空の URL を持つ reference は no_references 警告を発行すること"


# ---------------------------------------------------------------------------
# unsupported claim check
# ---------------------------------------------------------------------------


def test_unsupported_claim_check_suppressed_when_guardrail_set() -> None:
    draft = _make_draft(
        validation_hints=("guardrail:no_unsupported_claims",),
        warnings=(),
    )
    result = validate_draft_output(draft)
    codes = {i.code for i in result.issues}
    assert "unsupported_claim_risk" not in codes


def test_unsupported_claim_check_emits_warning_when_no_guardrail_and_no_warnings() -> None:
    draft = _make_draft(validation_hints=(), warnings=())
    result = validate_draft_output(draft)
    found = [
        i for i in result.issues if i.code == "unsupported_claim_risk" and i.severity == "warning"
    ]
    assert found


def test_unsupported_claim_check_suppressed_when_warnings_present() -> None:
    draft = _make_draft(
        validation_hints=(),
        warnings=("出典にない断定を避けてください。",),
    )
    result = validate_draft_output(draft)
    codes = {i.code for i in result.issues}
    assert "unsupported_claim_risk" not in codes


# ---------------------------------------------------------------------------
# dangerous detail guardrail
# ---------------------------------------------------------------------------


def test_dangerous_detail_not_detected_for_clean_draft() -> None:
    result = validate_draft_output(_make_draft())
    codes = {i.code for i in result.issues}
    assert "dangerous_detail_detected" not in codes


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("title", "exploit コードを使った攻撃手順について"),
        ("summary_for_users", "proof of concept が公開されています"),
        ("impact", "PoC が確認されました"),
        ("required_actions", ("reverse shell を使った実証が可能です",)),
        ("admin_actions", ("attack steps を確認してください",)),
    ],
)
def test_dangerous_detail_detected_in_various_fields(field_name: str, value: object) -> None:
    draft = _make_draft(**{field_name: value})
    result = validate_draft_output(draft)
    errors = [
        i for i in result.issues if i.code == "dangerous_detail_detected" and i.severity == "error"
    ]
    assert errors, f"{field_name} に危険パターンが検出されること"
    assert errors[0].reviewer_hint is not None


def test_dangerous_detail_guardrail_hint_present_but_no_dangerous_text() -> None:
    draft = _make_draft(
        validation_hints=("guardrail:no_attack_steps_or_poc",),
    )
    result = validate_draft_output(draft)
    codes = {i.code for i in result.issues}
    assert "dangerous_detail_detected" not in codes


def test_dangerous_pattern_no_false_positive_on_epoch() -> None:
    """再 ASCII フラグにより \\bpoc\\b が 'epoch' 内部の 'poc' にマッチしないことを確認する。"""
    result = validate_draft_output(_make_draft(title="Unix epoch timestamp の確認"))
    codes = {i.code for i in result.issues}
    assert "dangerous_detail_detected" not in codes


def test_dangerous_pattern_poc_adjacent_japanese_detected() -> None:
    """re.ASCII により 'PoCが発見' のように日本語に隣接した PoC も検出されることを確認する。"""
    result = validate_draft_output(_make_draft(title="PoCが発見されました"))
    errors = [i for i in result.issues if i.code == "dangerous_detail_detected"]
    assert errors, "日本語に隣接した PoC も検出されること"


# ---------------------------------------------------------------------------
# uncertainty wording check
# ---------------------------------------------------------------------------


def test_uncertainty_notes_present_no_info() -> None:
    result = validate_draft_output(_make_draft())
    codes = {i.code for i in result.issues}
    assert "no_uncertainty_notes" not in codes


def test_uncertainty_notes_empty_emits_info() -> None:
    result = validate_draft_output(_make_draft(uncertainty_notes=()))
    found = [i for i in result.issues if i.code == "no_uncertainty_notes" and i.severity == "info"]
    assert found
    assert found[0].reviewer_hint is not None


# ---------------------------------------------------------------------------
# regeneration request reason
# ---------------------------------------------------------------------------


def test_regeneration_hints_populated_when_errors_present() -> None:
    result = validate_draft_output(_make_draft(title=""))
    assert result.regeneration_hints
    assert any("title" in hint.lower() or "必須" in hint for hint in result.regeneration_hints)


def test_regeneration_hints_empty_when_no_errors() -> None:
    result = validate_draft_output(_make_draft())
    assert result.regeneration_hints == ()


# ---------------------------------------------------------------------------
# reviewer warning 集約
# ---------------------------------------------------------------------------


def test_reviewer_warnings_populated_from_issues_with_hints() -> None:
    result = validate_draft_output(_make_draft(references=()))
    assert result.reviewer_warnings
    assert all(isinstance(w, str) for w in result.reviewer_warnings)


def test_reviewer_warnings_empty_when_no_hints() -> None:
    result = validate_draft_output(_make_draft())
    assert result.reviewer_warnings == ()


# ---------------------------------------------------------------------------
# インポートテスト
# ---------------------------------------------------------------------------


def test_import_from_llm_package() -> None:
    from spautopost.llm import (  # noqa: F401
        ValidationIssue,
        ValidationResult,
        validate_draft_output,
    )


def test_validate_draft_output_returns_validation_result() -> None:
    result = validate_draft_output(_make_draft())
    assert isinstance(result, ValidationResult)
