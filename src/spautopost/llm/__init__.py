"""LLM provider interface と test_mock provider。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal, Protocol, runtime_checkable

from spautopost.config import LLMConfig

ProviderType = Literal[
    "production_api", "production_flow", "generic_api", "test_mock", "test_manual"
]
TargetAudience = Literal["general_users", "administrators", "mixed"]
Urgency = Literal["emergency", "high", "normal", "low"]

Reference = Mapping[str, str]
AdvisoryPayload = Mapping[str, object]


class LLMProviderConfigError(ValueError):
    """LLM provider 設定または構築の失敗。Secret 値は含めない。"""


class LLMProviderError(RuntimeError):
    """LLM provider 呼び出しの失敗。Secret 値は含めない。

    ``is_retryable`` が True の場合、上位でリトライ可能であることを示す。
    """

    def __init__(self, message: str, *, is_retryable: bool) -> None:
        super().__init__(message)
        self.is_retryable = is_retryable


@dataclass(frozen=True)
class DraftInput:
    """LLM provider に渡す掲示板原稿生成入力。"""

    advisory: AdvisoryPayload | Sequence[AdvisoryPayload]
    target_audience: TargetAudience
    target_language: str
    urgency: Urgency
    template_id: str
    prompt_version: str
    references: Sequence[Reference]


@dataclass(frozen=True)
class DraftOutput:
    """LLM provider から返す掲示板原稿。"""

    title: str
    summary_for_users: str
    impact: str
    required_actions: Sequence[str]
    references: Sequence[Reference]
    warnings: Sequence[str] = ()
    admin_actions: Sequence[str] = ()
    deadline: str | None = None
    uncertainty_notes: Sequence[str] = ()
    source_mapping: Mapping[str, str] = field(default_factory=dict)
    validation_hints: Sequence[str] = ()
    generation_input_hash: str | None = None


@dataclass(frozen=True)
class ProviderMetadata:
    """provider の監査用 metadata。"""

    provider_name: str
    provider_type: ProviderType
    model: str | None
    prompt_version: str | None


@dataclass(frozen=True)
class ProviderStatus:
    """provider config validation の結果。"""

    valid: bool
    issues: Sequence[str]
    metadata: ProviderMetadata


@runtime_checkable
class LLMProvider(Protocol):
    """LLM provider の最小 interface。"""

    def validate_config(self) -> ProviderStatus: ...

    def generate_draft(self, draft_input: DraftInput) -> DraftOutput: ...

    def get_provider_metadata(self) -> ProviderMetadata: ...


class MockLLMProvider:
    """外部通信しない deterministic provider。"""

    def __init__(
        self,
        *,
        fixture: DraftOutput | None = None,
        prompt_version: str | None = None,
        provider_name: str = "test_mock",
    ) -> None:
        self._fixture = fixture
        self._metadata = ProviderMetadata(
            provider_name=provider_name,
            provider_type="test_mock",
            model=None,
            prompt_version=prompt_version,
        )

    def validate_config(self) -> ProviderStatus:
        return ProviderStatus(valid=True, issues=(), metadata=self._metadata)

    def generate_draft(self, draft_input: DraftInput) -> DraftOutput:
        if self._fixture is not None:
            return self._fixture
        from .templates import compose_sharepoint_draft

        return compose_sharepoint_draft(draft_input)

    def get_provider_metadata(self) -> ProviderMetadata:
        return self._metadata


def build_llm_provider(config: LLMConfig, *, fixture: DraftOutput | None = None) -> LLMProvider:
    """検証済み LLMConfig から provider を構築する。"""
    if config.provider == "test_mock":
        return MockLLMProvider(fixture=fixture, prompt_version=config.prompt_version)
    if config.provider == "production_api":
        from .azure_openai import AzureOpenAIProvider

        if config.azure is None:
            raise LLMProviderConfigError(
                "llm.azure config is required when provider=production_api"
            )
        return AzureOpenAIProvider(config.azure, prompt_version=config.prompt_version)
    if config.provider == "generic_api":
        from .generic_provider import GenericApiLLMProvider

        return GenericApiLLMProvider(config)
    raise LLMProviderConfigError(
        f"llm provider {config.provider!r} is not supported; "
        "only 'test_mock', 'production_api' and 'generic_api' are implemented"
    )


__all__ = [
    "DraftInput",
    "DraftOutput",
    "LLMProvider",
    "LLMProviderConfigError",
    "LLMProviderError",
    "MockLLMProvider",
    "ProviderMetadata",
    "ProviderStatus",
    "build_llm_provider",
]
