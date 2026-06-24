"""LLM provider interface と test_mock provider。"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
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
        title = _advisory_title(draft_input.advisory)
        input_hash = _input_hash(draft_input)
        return DraftOutput(
            title=f"{_urgency_prefix(draft_input.urgency)} {title}".strip(),
            summary_for_users=f"{title} について、公開情報に基づく確認が必要です。",
            impact="影響範囲は入力された advisory と references を確認してください。",
            required_actions=("参考情報を確認し、必要な更新または回避策を適用してください。",),
            admin_actions=("管理者は対象製品と適用状況を確認してください。",),
            references=tuple(draft_input.references),
            warnings=("test_mock provider generated this deterministic draft.",),
            validation_hints=("human_review_required",),
            generation_input_hash=input_hash,
        )

    def get_provider_metadata(self) -> ProviderMetadata:
        return self._metadata


def build_llm_provider(config: LLMConfig, *, fixture: DraftOutput | None = None) -> LLMProvider:
    """検証済み LLMConfig から provider を構築する。"""
    if config.provider == "test_mock":
        return MockLLMProvider(fixture=fixture, prompt_version=config.prompt_version)
    raise LLMProviderConfigError(f"llm provider is not implemented in Issue #6: {config.provider}")


def _advisory_title(advisory: AdvisoryPayload | Sequence[AdvisoryPayload]) -> str:
    first = advisory if isinstance(advisory, Mapping) else next(iter(advisory), {})
    title = first.get("title")
    return title if isinstance(title, str) and title else "SPAutoPost mock draft"


def _urgency_prefix(urgency: Urgency) -> str:
    return {
        "emergency": "[緊急]",
        "high": "[重要]",
        "normal": "[注意喚起]",
        "low": "[参考]",
    }[urgency]


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
    "DraftInput",
    "DraftOutput",
    "LLMProvider",
    "LLMProviderConfigError",
    "MockLLMProvider",
    "ProviderMetadata",
    "ProviderStatus",
    "build_llm_provider",
]
