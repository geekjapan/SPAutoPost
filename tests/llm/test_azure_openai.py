"""AzureOpenAIProvider の単体テスト。実 endpoint は使わず urllib をモックする。"""

from __future__ import annotations

import json
import os
import urllib.error
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from spautopost.config import AzureOpenAIConfig, LLMConfig
from spautopost.llm import (
    DraftInput,
    DraftOutput,
    LLMProvider,
    LLMProviderError,
    build_llm_provider,
)
from spautopost.llm.azure_openai import AzureOpenAIProvider

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

_VALID_AZURE_CONFIG = AzureOpenAIConfig(
    endpoint="https://example.openai.azure.com",
    deployment="gpt-4o",
    api_version="2024-02-01",
    auth_type="api_key",
    api_key_ref="env:AZURE_OPENAI_API_KEY",
    timeout_secs=30,
    max_retries=2,
    production_approved=True,
)


def _draft_input() -> DraftInput:
    return DraftInput(
        advisory={
            "title": "Example CVE の脆弱性",
            "summary": "権限昇格が起きる可能性があります。",
            "affected_products": ["Example Product v1.0"],
            "deadline": "2026-07-01",
            "patch_available": True,
            "exploit_status": "public",
        },
        target_audience="mixed",
        target_language="ja-JP",
        urgency="high",
        template_id="sharepoint-announcement-m1",
        prompt_version="v1",
        references=({"title": "Vendor advisory", "url": "https://example.test/advisory"},),
    )


def _api_response(*, extra: dict[str, Any] | None = None) -> bytes:
    """Azure OpenAI API の正常レスポンスを模擬する。"""
    draft_content = {
        "title": "[重要] Example CVE の脆弱性 対応について",
        "summary_for_users": "権限昇格につながる脆弱性が報告されました。更新プログラムを適用してください。",  # noqa: E501
        "impact": "Example Product v1.0 を使用している場合に影響を受ける可能性があります。",  # noqa: E501
        "required_actions": ["対象製品の利用有無を確認する", "公式パッチを適用する"],
        "admin_actions": ["管理対象環境のパッチ適用状況を確認する"],
        "deadline": "2026-07-01",
        "references": [{"title": "Vendor advisory", "url": "https://example.test/advisory"}],
        "warnings": ["出典を確認してください"],
        "uncertainty_notes": [],
        "validation_hints": [
            "guardrail:no_unsupported_claims",
            "guardrail:no_attack_steps_or_poc",
            "human_review_required",
        ],
    }
    if extra:
        draft_content.update(extra)
    payload = {
        "choices": [{"message": {"content": json.dumps(draft_content)}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300},
    }
    return json.dumps(payload).encode()


def _mock_urlopen(response_bytes: bytes, *, status: int = 200) -> MagicMock:
    """urllib.request.urlopen の正常応答モックを作る。"""
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_bytes
    mock_resp.status = status
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ---------------------------------------------------------------------------
# validate_config tests
# ---------------------------------------------------------------------------


def test_validate_config_returns_valid_for_complete_config() -> None:
    provider = AzureOpenAIProvider(_VALID_AZURE_CONFIG, prompt_version="v1")

    status = provider.validate_config()

    assert status.valid is True
    assert status.issues == ()
    assert status.metadata.provider_type == "production_api"


def test_validate_config_fails_when_production_approved_is_false() -> None:
    cfg = AzureOpenAIConfig(
        endpoint="https://example.openai.azure.com",
        deployment="gpt-4o",
        api_version="2024-02-01",
        auth_type="api_key",
        api_key_ref="env:AZURE_OPENAI_API_KEY",
        timeout_secs=30,
        max_retries=2,
        production_approved=False,
    )
    provider = AzureOpenAIProvider(cfg)

    status = provider.validate_config()

    assert status.valid is False
    assert any("production_approved" in issue for issue in status.issues)


def test_validate_config_fails_when_endpoint_is_empty() -> None:
    cfg = AzureOpenAIConfig(
        endpoint="",
        deployment="gpt-4o",
        api_version="2024-02-01",
        auth_type="api_key",
        api_key_ref="env:AZURE_OPENAI_API_KEY",
        timeout_secs=30,
        max_retries=2,
        production_approved=True,
    )
    provider = AzureOpenAIProvider(cfg)

    status = provider.validate_config()

    assert status.valid is False
    assert any("endpoint" in issue for issue in status.issues)


def test_validate_config_fails_for_managed_identity_auth_type() -> None:
    cfg = AzureOpenAIConfig(
        endpoint="https://example.openai.azure.com",
        deployment="gpt-4o",
        api_version="2024-02-01",
        auth_type="managed_identity",
        api_key_ref=None,
        timeout_secs=30,
        max_retries=2,
        production_approved=True,
    )
    provider = AzureOpenAIProvider(cfg)

    status = provider.validate_config()

    assert status.valid is False
    assert any("managed_identity" in issue for issue in status.issues)


def test_validate_config_does_not_include_secret_values_in_issues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_value = "actual-secret-key-content-xyz"  # noqa: S105
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", secret_value)
    cfg = AzureOpenAIConfig(
        endpoint="",
        deployment="",
        api_version="2024-02-01",
        auth_type="api_key",
        api_key_ref=None,
        timeout_secs=30,
        max_retries=2,
        production_approved=False,
    )
    provider = AzureOpenAIProvider(cfg)

    status = provider.validate_config()

    # issues に実際の Secret 値・Bearer トークンが漏洩していないこと
    combined = " ".join(status.issues)
    assert secret_value not in combined
    assert "Bearer" not in combined


# ---------------------------------------------------------------------------
# get_provider_metadata tests
# ---------------------------------------------------------------------------


def test_get_provider_metadata_returns_correct_metadata() -> None:
    provider = AzureOpenAIProvider(_VALID_AZURE_CONFIG, prompt_version="v2")

    meta = provider.get_provider_metadata()

    assert isinstance(provider, LLMProvider)
    assert meta.provider_name == "azure-openai"
    assert meta.provider_type == "production_api"
    assert meta.model == "gpt-4o"
    assert meta.prompt_version == "v2"


# ---------------------------------------------------------------------------
# generate_draft tests（成功パス）
# ---------------------------------------------------------------------------


def test_generate_draft_returns_draft_output_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-value")
    provider = AzureOpenAIProvider(
        _VALID_AZURE_CONFIG, prompt_version="v1", _sleep_fn=lambda _: None
    )

    with patch("urllib.request.urlopen", return_value=_mock_urlopen(_api_response())):
        result = provider.generate_draft(_draft_input())

    assert isinstance(result, DraftOutput)
    assert result.title == "[重要] Example CVE の脆弱性 対応について"
    assert result.generation_input_hash is not None
    assert len(result.generation_input_hash) == 64  # SHA-256 hex


def test_generate_draft_sets_audit_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-value")
    provider = AzureOpenAIProvider(
        _VALID_AZURE_CONFIG, prompt_version="v1", _sleep_fn=lambda _: None
    )

    with patch("urllib.request.urlopen", return_value=_mock_urlopen(_api_response())):
        result = provider.generate_draft(_draft_input())

    assert result.source_mapping.get("provider_name") == "azure-openai"
    assert result.source_mapping.get("model") == "gpt-4o"
    assert result.source_mapping.get("prompt_version") == "v1"
    # token_usage が付与されている
    assert "token_usage" in result.source_mapping


def test_generate_draft_does_not_include_api_key_in_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_value = "super-secret-api-key-xyz"  # noqa: S105
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", secret_value)
    provider = AzureOpenAIProvider(
        _VALID_AZURE_CONFIG, prompt_version="v1", _sleep_fn=lambda _: None
    )

    with patch("urllib.request.urlopen", return_value=_mock_urlopen(_api_response())):
        result = provider.generate_draft(_draft_input())

    # source_mapping の全値に Secret が含まれていないこと
    for v in result.source_mapping.values():
        assert secret_value not in str(v)
    assert secret_value not in (result.generation_input_hash or "")


def test_generate_draft_sets_guardrail_validation_hints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-value")
    provider = AzureOpenAIProvider(
        _VALID_AZURE_CONFIG, prompt_version="v1", _sleep_fn=lambda _: None
    )

    with patch("urllib.request.urlopen", return_value=_mock_urlopen(_api_response())):
        result = provider.generate_draft(_draft_input())

    assert "guardrail:no_unsupported_claims" in result.validation_hints
    assert "guardrail:no_attack_steps_or_poc" in result.validation_hints
    assert "human_review_required" in result.validation_hints


# ---------------------------------------------------------------------------
# generate_draft tests（config 無効時のガード）
# ---------------------------------------------------------------------------


def test_generate_draft_raises_when_config_invalid() -> None:
    cfg = AzureOpenAIConfig(
        endpoint="",
        deployment="gpt-4o",
        api_version="2024-02-01",
        auth_type="api_key",
        api_key_ref="env:AZURE_OPENAI_API_KEY",
        timeout_secs=30,
        max_retries=0,
        production_approved=False,
    )
    provider = AzureOpenAIProvider(cfg, _sleep_fn=lambda _: None)

    with pytest.raises(LLMProviderError) as exc:
        provider.generate_draft(_draft_input())

    assert exc.value.is_retryable is False


def test_generate_draft_raises_when_api_key_env_not_set() -> None:
    provider = AzureOpenAIProvider(_VALID_AZURE_CONFIG, _sleep_fn=lambda _: None)

    # 環境変数を未設定にする
    env_without_key = {k: v for k, v in os.environ.items() if k != "AZURE_OPENAI_API_KEY"}
    with patch.dict(os.environ, env_without_key, clear=True):
        with pytest.raises(LLMProviderError) as exc:
            provider.generate_draft(_draft_input())

    error_msg = str(exc.value)
    assert "AZURE_OPENAI_API_KEY" in error_msg
    # Secret 値がエラーメッセージに含まれていないこと（この場合値はないが念のため）
    assert "env:" not in error_msg.replace("AZURE_OPENAI_API_KEY", "")


# ---------------------------------------------------------------------------
# generate_draft tests（エラーハンドリング）
# ---------------------------------------------------------------------------


def test_generate_draft_raises_non_retryable_on_http_401(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-value")
    provider = AzureOpenAIProvider(_VALID_AZURE_CONFIG, _sleep_fn=lambda _: None)
    http_error = urllib.error.HTTPError(url="", code=401, msg="Unauthorized", hdrs=None, fp=None)  # type: ignore[arg-type]

    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(LLMProviderError) as exc:
            provider.generate_draft(_draft_input())

    assert exc.value.is_retryable is False


def test_generate_draft_raises_non_retryable_on_http_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-value")
    provider = AzureOpenAIProvider(_VALID_AZURE_CONFIG, _sleep_fn=lambda _: None)
    http_error = urllib.error.HTTPError(url="", code=400, msg="Bad Request", hdrs=None, fp=None)  # type: ignore[arg-type]

    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(LLMProviderError) as exc:
            provider.generate_draft(_draft_input())

    assert exc.value.is_retryable is False


def test_generate_draft_raises_retryable_on_http_429(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-value")
    cfg = AzureOpenAIConfig(
        endpoint="https://example.openai.azure.com",
        deployment="gpt-4o",
        api_version="2024-02-01",
        auth_type="api_key",
        api_key_ref="env:AZURE_OPENAI_API_KEY",
        timeout_secs=30,
        max_retries=0,  # retry なし
        production_approved=True,
    )
    provider = AzureOpenAIProvider(cfg, _sleep_fn=lambda _: None)
    http_error = urllib.error.HTTPError(  # type: ignore[arg-type]
        url="", code=429, msg="Too Many Requests", hdrs=None, fp=None
    )

    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(LLMProviderError) as exc:
            provider.generate_draft(_draft_input())

    assert exc.value.is_retryable is True


def test_generate_draft_raises_retryable_on_http_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-value")
    cfg = AzureOpenAIConfig(
        endpoint="https://example.openai.azure.com",
        deployment="gpt-4o",
        api_version="2024-02-01",
        auth_type="api_key",
        api_key_ref="env:AZURE_OPENAI_API_KEY",
        timeout_secs=30,
        max_retries=0,
        production_approved=True,
    )
    provider = AzureOpenAIProvider(cfg, _sleep_fn=lambda _: None)
    http_error = urllib.error.HTTPError(  # type: ignore[arg-type]
        url="", code=500, msg="Internal Server Error", hdrs=None, fp=None
    )

    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(LLMProviderError) as exc:
            provider.generate_draft(_draft_input())

    assert exc.value.is_retryable is True


def test_generate_draft_raises_retryable_on_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-value")
    cfg = AzureOpenAIConfig(
        endpoint="https://example.openai.azure.com",
        deployment="gpt-4o",
        api_version="2024-02-01",
        auth_type="api_key",
        api_key_ref="env:AZURE_OPENAI_API_KEY",
        timeout_secs=30,
        max_retries=0,
        production_approved=True,
    )
    provider = AzureOpenAIProvider(cfg, _sleep_fn=lambda _: None)

    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        with pytest.raises(LLMProviderError) as exc:
            provider.generate_draft(_draft_input())

    assert exc.value.is_retryable is True


def test_generate_draft_raises_non_retryable_when_response_json_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-value")
    provider = AzureOpenAIProvider(_VALID_AZURE_CONFIG, _sleep_fn=lambda _: None)
    # choices[0].message.content の JSON が DraftOutput に変換できない
    bad_content = json.dumps(
        {
            "choices": [{"message": {"content": json.dumps({"unexpected_field": "value"})}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        }
    ).encode()

    with patch("urllib.request.urlopen", return_value=_mock_urlopen(bad_content)):
        with pytest.raises(LLMProviderError) as exc:
            provider.generate_draft(_draft_input())

    assert exc.value.is_retryable is False


def test_generate_draft_raises_non_retryable_on_invalid_outer_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-value")
    provider = AzureOpenAIProvider(_VALID_AZURE_CONFIG, _sleep_fn=lambda _: None)
    invalid_bytes = b"not json at all"

    with patch("urllib.request.urlopen", return_value=_mock_urlopen(invalid_bytes)):
        with pytest.raises(LLMProviderError) as exc:
            provider.generate_draft(_draft_input())

    assert exc.value.is_retryable is False


# ---------------------------------------------------------------------------
# retry tests
# ---------------------------------------------------------------------------


def test_generate_draft_retries_on_http_429_and_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-value")
    sleep_calls: list[float] = []
    provider = AzureOpenAIProvider(
        _VALID_AZURE_CONFIG,
        prompt_version="v1",
        _sleep_fn=lambda s: sleep_calls.append(s),
    )

    http_error = urllib.error.HTTPError(  # type: ignore[arg-type]
        url="", code=429, msg="Too Many Requests", hdrs=None, fp=None
    )
    success_resp = _mock_urlopen(_api_response())

    # 1回目: 429 → 2回目: 成功
    side_effects = [http_error, success_resp]
    with patch("urllib.request.urlopen", side_effect=side_effects):
        result = provider.generate_draft(_draft_input())

    assert isinstance(result, DraftOutput)
    assert len(sleep_calls) == 1  # バックオフが 1 回発生した


def test_generate_draft_exhausts_retries_and_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key-value")
    sleep_calls: list[float] = []
    cfg = AzureOpenAIConfig(
        endpoint="https://example.openai.azure.com",
        deployment="gpt-4o",
        api_version="2024-02-01",
        auth_type="api_key",
        api_key_ref="env:AZURE_OPENAI_API_KEY",
        timeout_secs=30,
        max_retries=2,
        production_approved=True,
    )
    provider = AzureOpenAIProvider(cfg, _sleep_fn=lambda s: sleep_calls.append(s))
    http_error = urllib.error.HTTPError(url="", code=500, msg="Server Error", hdrs=None, fp=None)  # type: ignore[arg-type]

    with patch("urllib.request.urlopen", side_effect=[http_error] * 10):
        with pytest.raises(LLMProviderError) as exc:
            provider.generate_draft(_draft_input())

    assert exc.value.is_retryable is True
    assert len(sleep_calls) == 2  # max_retries=2 → 2 回バックオフ


# ---------------------------------------------------------------------------
# build_llm_provider tests
# ---------------------------------------------------------------------------


def test_build_llm_provider_selects_azure_openai_for_production_api() -> None:
    config = LLMConfig(
        provider="production_api",
        prompt_version="v1",
        azure=_VALID_AZURE_CONFIG,
    )

    provider = build_llm_provider(config)

    assert isinstance(provider, AzureOpenAIProvider)
    meta = provider.get_provider_metadata()
    assert meta.provider_type == "production_api"
    assert meta.provider_name == "azure-openai"


def test_build_llm_provider_raises_without_azure_config_for_production_api() -> None:
    config = LLMConfig(provider="production_api", prompt_version="v1")

    with pytest.raises(LLMProviderError):
        build_llm_provider(config)
