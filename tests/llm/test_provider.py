"""LLM provider interface と mock provider の単体テスト。"""

from __future__ import annotations

import pytest

from spautopost.config import LLMConfig
from spautopost.llm import (
    DraftInput,
    DraftOutput,
    LLMProvider,
    LLMProviderConfigError,
    MockLLMProvider,
    build_llm_provider,
)
from spautopost.llm.templates import (
    SHAREPOINT_ANNOUNCEMENT_PROMPT_TEMPLATE,
    compose_sharepoint_draft,
)


def _draft_input() -> DraftInput:
    return DraftInput(
        advisory={
            "title": "Example Product の脆弱性",
            "summary": "権限昇格につながる可能性があります。",
            "affected_products": ["Example Product"],
            "deadline": "2026-07-01",
            "patch_available": True,
            "exploit_status": "unknown",
        },
        target_audience="mixed",
        target_language="ja-JP",
        urgency="high",
        template_id="sharepoint-m1",
        prompt_version="v1",
        references=({"title": "Vendor advisory", "url": "https://example.test/advisory"},),
    )


def test_mock_provider_returns_fixture_response() -> None:
    fixture = DraftOutput(
        title="[重要] Example Product の脆弱性対応について",
        summary_for_users="更新プログラムを適用してください。",
        impact="出典に記載された影響があります。",
        required_actions=("更新プログラムを適用する",),
        references=({"title": "Vendor advisory", "url": "https://example.test/advisory"},),
    )
    provider = MockLLMProvider(fixture=fixture)

    assert provider.generate_draft(_draft_input()) == fixture


def test_mock_provider_fallback_is_deterministic() -> None:
    provider = MockLLMProvider()
    draft_input = _draft_input()

    first = provider.generate_draft(draft_input)
    second = provider.generate_draft(draft_input)

    assert first == second
    assert first.title == "[重要] Example Product の脆弱性 対応について"
    assert first.generation_input_hash is not None


def test_mock_provider_exposes_metadata_and_valid_status() -> None:
    provider = MockLLMProvider(prompt_version="v2")

    metadata = provider.get_provider_metadata()
    status = provider.validate_config()

    assert isinstance(provider, LLMProvider)
    assert metadata.provider_type == "test_mock"
    assert metadata.prompt_version == "v2"
    assert status.valid is True
    assert status.issues == ()


def test_build_llm_provider_selects_test_mock() -> None:
    provider = build_llm_provider(LLMConfig(provider="test_mock", prompt_version="v1"))

    assert isinstance(provider, MockLLMProvider)
    assert provider.get_provider_metadata().prompt_version == "v1"


@pytest.mark.parametrize(
    "provider", ["production_api", "production_flow", "generic_api", "test_manual"]
)
def test_build_llm_provider_rejects_unimplemented_provider_types(provider: str) -> None:
    with pytest.raises(LLMProviderConfigError) as excinfo:
        build_llm_provider(LLMConfig(provider=provider, prompt_version="v1"))

    message = str(excinfo.value)
    assert provider in message
    assert "Issue #6" not in message
    assert "test_mock" in message


@pytest.mark.parametrize(
    "advisory",
    [
        {"title": "Single mapping advisory"},
        [{"title": "First sequence advisory"}, {"title": "Second"}],
        [],
        ["malformed", 123],
        "unexpected string",
    ],
)
def test_mock_provider_handles_unexpected_advisory_shapes(advisory: object) -> None:
    draft_input = DraftInput(
        advisory=advisory,  # type: ignore[arg-type]
        target_audience="mixed",
        target_language="ja-JP",
        urgency="high",
        template_id="sharepoint-m1",
        prompt_version="v1",
        references=(),
    )

    draft = MockLLMProvider().generate_draft(draft_input)

    assert isinstance(draft.title, str)
    assert draft.title.strip() != ""


def test_sharepoint_composition_template_keeps_issue_8_sections() -> None:
    draft_input = _draft_input()

    draft = compose_sharepoint_draft(draft_input, generation_input_hash="hash-1")

    assert draft.references == draft_input.references
    assert draft.summary_for_users
    assert draft.required_actions
    assert draft.admin_actions
    assert draft.deadline == "2026-07-01"
    assert draft.source_mapping["prompt_version"] == "v1"
    assert draft.generation_input_hash == "hash-1"


def test_sharepoint_composition_template_records_guardrails() -> None:
    draft = compose_sharepoint_draft(_draft_input())

    assert "PoC" in SHAREPOINT_ANNOUNCEMENT_PROMPT_TEMPLATE
    assert "guardrail:no_unsupported_claims" in draft.validation_hints
    assert "guardrail:no_attack_steps_or_poc" in draft.validation_hints
    assert all(
        "exploit 手順" not in text for text in (*draft.required_actions, *draft.admin_actions)
    )


def test_sharepoint_composition_template_normalizes_review_flags() -> None:
    draft_input = DraftInput(
        advisory={
            "title": "重複製品の注意喚起",
            "affected_products": ["Example Product", "Example Product"],
            "patch_available": " UNKNOWN ",
            "exploit_status": "Unknown",
        },
        target_audience="mixed",
        target_language="ja-JP",
        urgency="normal",
        template_id="sharepoint-m1",
        prompt_version="v1",
        references=({"label": "Vendor advisory", "url": "https://example.test/advisory"},),
    )

    draft = compose_sharepoint_draft(draft_input)

    assert draft.impact.count("Example Product") == 1
    assert "patch availability が不明です。" in draft.uncertainty_notes
    assert "exploit status が不明です。" in draft.uncertainty_notes
