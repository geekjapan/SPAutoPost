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


def _draft_input() -> DraftInput:
    return DraftInput(
        advisory={"title": "Example Product の脆弱性", "affected_products": ["Example Product"]},
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
    assert first.title == "[重要] Example Product の脆弱性"
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

    assert provider in str(excinfo.value)
