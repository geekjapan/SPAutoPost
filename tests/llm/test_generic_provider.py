"""GenericApiLLMProvider の単体テスト（mock HTTP のみ、実 API 不使用）。"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from spautopost.config import LLMConfig
from spautopost.llm import DraftInput, LLMProvider, build_llm_provider
from spautopost.llm.generic_provider import GenericApiLLMProvider, LLMProviderError

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _config(**overrides: object) -> LLMConfig:
    defaults: dict[str, object] = {
        "provider": "generic_api",
        "prompt_version": "v1",
        "endpoint_url": "https://api.example.test/v1/chat/completions",
        "model": "gpt-4o",
        "auth_env_var": "LLM_API_KEY",
        "timeout_seconds": 10,
        "max_retries": 1,
    }
    defaults.update(overrides)
    return LLMConfig(**defaults)  # type: ignore[arg-type]


def _draft_input() -> DraftInput:
    return DraftInput(
        advisory={
            "title": "Test CVE",
            "summary": "Test summary.",
            "affected_products": ["TestProduct"],
            "patch_available": True,
            "exploit_status": "unknown",
        },
        target_audience="mixed",
        target_language="ja-JP",
        urgency="normal",
        template_id="sharepoint-m1",
        prompt_version="v1",
        references=({"title": "Test ref", "url": "https://example.test/ref"},),
    )


def _api_response_body(content: str) -> bytes:
    return json.dumps({"choices": [{"message": {"content": content}}]}).encode("utf-8")


def _valid_content() -> str:
    return json.dumps(
        {
            "title": "[注意喚起] Test CVE 対応について",
            "summary_for_users": "テスト要約です。",
            "impact": "TestProduct に影響があります。",
            "required_actions": ["対象製品を確認してください。"],
            "references": [{"title": "Test ref", "url": "https://example.test/ref"}],
            "admin_actions": ["管理者は適用状況を確認してください。"],
            "deadline": None,
            "warnings": [],
            "uncertainty_notes": ["exploit status が不明です。"],
        }
    )


def _mock_urlopen(content: str) -> MagicMock:
    """urlopen の context manager を模倣する mock。"""
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    mock.read.return_value = _api_response_body(content)
    return mock


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


class TestValidateConfig:
    def test_valid_config_returns_valid_status(self) -> None:
        provider = GenericApiLLMProvider(_config())
        status = provider.validate_config()
        assert status.valid is True
        assert status.issues == ()

    def test_missing_endpoint_url_returns_invalid(self) -> None:
        provider = GenericApiLLMProvider(_config(endpoint_url=None))
        status = provider.validate_config()
        assert status.valid is False
        assert any("endpoint_url" in issue for issue in status.issues)

    def test_missing_model_returns_invalid(self) -> None:
        provider = GenericApiLLMProvider(_config(model=None))
        status = provider.validate_config()
        assert status.valid is False
        assert any("model" in issue for issue in status.issues)

    def test_missing_auth_env_var_returns_invalid(self) -> None:
        provider = GenericApiLLMProvider(_config(auth_env_var=None))
        status = provider.validate_config()
        assert status.valid is False
        assert any("auth_env_var" in issue for issue in status.issues)

    def test_http_endpoint_url_returns_invalid(self) -> None:
        provider = GenericApiLLMProvider(_config(endpoint_url="http://api.example.test/v1/chat"))
        status = provider.validate_config()
        assert status.valid is False
        assert any("https" in issue for issue in status.issues)

    def test_status_metadata_has_correct_provider_type(self) -> None:
        provider = GenericApiLLMProvider(_config())
        status = provider.validate_config()
        assert status.metadata.provider_type == "generic_api"


# ---------------------------------------------------------------------------
# provider metadata
# ---------------------------------------------------------------------------


class TestProviderMetadata:
    def test_metadata_provider_type_is_generic_api(self) -> None:
        provider = GenericApiLLMProvider(_config())
        assert provider.get_provider_metadata().provider_type == "generic_api"

    def test_metadata_contains_model(self) -> None:
        provider = GenericApiLLMProvider(_config(model="gpt-4o"))
        assert provider.get_provider_metadata().model == "gpt-4o"

    def test_metadata_does_not_contain_secret(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_API_KEY", "sk-secret-token-value")
        provider = GenericApiLLMProvider(_config())
        metadata = provider.get_provider_metadata()
        # ProviderMetadata の全フィールド文字列表現に secret が含まれないこと
        meta_str = str(metadata)
        assert "sk-secret-token-value" not in meta_str

    def test_metadata_uses_provider_name_from_config(self) -> None:
        provider = GenericApiLLMProvider(_config(provider_name="my-llm"))
        assert provider.get_provider_metadata().provider_name == "my-llm"

    def test_metadata_defaults_provider_name_when_not_set(self) -> None:
        provider = GenericApiLLMProvider(_config(provider_name=None))
        assert provider.get_provider_metadata().provider_name == "generic-api"

    def test_implements_llm_provider_protocol(self) -> None:
        provider = GenericApiLLMProvider(_config())
        assert isinstance(provider, LLMProvider)


# ---------------------------------------------------------------------------
# generate_draft — 正常系
# ---------------------------------------------------------------------------


class TestGenerateDraftSuccess:
    def test_returns_draft_output_from_valid_response(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        provider = GenericApiLLMProvider(_config())
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(_valid_content())):
            result = provider.generate_draft(_draft_input())
        assert result.title == "[注意喚起] Test CVE 対応について"
        assert result.summary_for_users == "テスト要約です。"
        assert "対象製品を確認してください。" in result.required_actions

    def test_draft_output_includes_provider_source_mapping(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        provider = GenericApiLLMProvider(_config())
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(_valid_content())):
            result = provider.generate_draft(_draft_input())
        assert result.source_mapping.get("provider_type") == "generic_api"
        assert result.source_mapping.get("prompt_version") == "v1"

    def test_draft_output_includes_guardrail_hints(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        provider = GenericApiLLMProvider(_config())
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(_valid_content())):
            result = provider.generate_draft(_draft_input())
        assert "guardrail:no_unsupported_claims" in result.validation_hints
        assert "guardrail:no_attack_steps_or_poc" in result.validation_hints
        assert "human_review_required" in result.validation_hints


# ---------------------------------------------------------------------------
# generate_draft — セキュリティ：Secret がリクエストに含まれない
# ---------------------------------------------------------------------------


class TestGenerateDraftSecurity:
    def test_secret_not_in_request_body(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LLM_API_KEY", "sk-super-secret-value")
        captured_bodies: list[str] = []

        def mock_urlopen(req: object, timeout: object) -> MagicMock:
            import urllib.request as ureq

            body = req.data.decode("utf-8") if isinstance(req, ureq.Request) and req.data else ""
            captured_bodies.append(body)
            return _mock_urlopen(_valid_content())

        provider = GenericApiLLMProvider(_config())
        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            provider.generate_draft(_draft_input())

        assert captured_bodies, "urlopen が呼ばれていない"
        assert "sk-super-secret-value" not in captured_bodies[0]

    def test_secret_not_in_error_message_on_4xx(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import urllib.error

        monkeypatch.setenv("LLM_API_KEY", "sk-very-secret")
        provider = GenericApiLLMProvider(_config(max_retries=0))
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                "https://api.example.test", 401, "Unauthorized", {}, None
            ),
        ):
            with pytest.raises(LLMProviderError) as exc_info:
                provider.generate_draft(_draft_input())
        assert "sk-very-secret" not in str(exc_info.value)

    def test_auth_header_sent_but_not_logged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Authorization ヘッダが設定されること（urlopen に渡されること）を確認する。"""
        monkeypatch.setenv("LLM_API_KEY", "sk-test-token")
        captured_headers: list[dict] = []

        def mock_urlopen(req: object, timeout: object) -> MagicMock:
            import urllib.request as ureq

            if isinstance(req, ureq.Request):
                captured_headers.append(dict(req.headers))
            return _mock_urlopen(_valid_content())

        provider = GenericApiLLMProvider(_config())
        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            provider.generate_draft(_draft_input())

        assert captured_headers
        # Authorization ヘッダが含まれている（値は確認しない）
        has_auth = any(
            "Authorization" in k or "authorization" in k.lower() for k in captured_headers[0]
        )
        assert has_auth


# ---------------------------------------------------------------------------
# generate_draft — エラー系
# ---------------------------------------------------------------------------


class TestGenerateDraftErrors:
    def test_missing_auth_env_var_raises_provider_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("LLM_API_KEY", raising=False)
        provider = GenericApiLLMProvider(_config())
        with pytest.raises(LLMProviderError) as exc_info:
            provider.generate_draft(_draft_input())
        assert exc_info.value.retryable is False
        # env var 名は含まれる（値は含まれない）
        assert "LLM_API_KEY" in str(exc_info.value)
        assert "not set" in str(exc_info.value)

    def test_http_5xx_raises_retryable_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import urllib.error

        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        provider = GenericApiLLMProvider(_config(max_retries=0))
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                "https://api.example.test", 503, "Service Unavailable", {}, None
            ),
        ):
            with pytest.raises(LLMProviderError) as exc_info:
                provider.generate_draft(_draft_input())
        assert exc_info.value.retryable is True

    def test_http_4xx_raises_non_retryable_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import urllib.error

        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        provider = GenericApiLLMProvider(_config(max_retries=0))
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                "https://api.example.test", 401, "Unauthorized", {}, None
            ),
        ):
            with pytest.raises(LLMProviderError) as exc_info:
                provider.generate_draft(_draft_input())
        assert exc_info.value.retryable is False

    def test_timeout_raises_retryable_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import urllib.error

        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        provider = GenericApiLLMProvider(_config(max_retries=0))
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("timed out"),
        ):
            with pytest.raises(LLMProviderError) as exc_info:
                provider.generate_draft(_draft_input())
        assert exc_info.value.retryable is True

    def test_invalid_json_content_raises_non_retryable_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        provider = GenericApiLLMProvider(_config(max_retries=0))
        with patch(
            "urllib.request.urlopen",
            return_value=_mock_urlopen("this is not json at all"),
        ):
            with pytest.raises(LLMProviderError) as exc_info:
                provider.generate_draft(_draft_input())
        assert exc_info.value.retryable is False

    def test_parse_error_message_does_not_include_response_body(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        secret_body = "SENSITIVE_RESPONSE_BODY_CONTENT"  # noqa: S105
        provider = GenericApiLLMProvider(_config(max_retries=0))
        with patch(
            "urllib.request.urlopen",
            return_value=_mock_urlopen(secret_body),
        ):
            with pytest.raises(LLMProviderError) as exc_info:
                provider.generate_draft(_draft_input())
        assert secret_body not in str(exc_info.value)

    def test_http_429_raises_retryable_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import urllib.error

        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        provider = GenericApiLLMProvider(_config(max_retries=0))
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                "https://api.example.test", 429, "Too Many Requests", {}, None
            ),
        ):
            with pytest.raises(LLMProviderError) as exc_info:
                provider.generate_draft(_draft_input())
        assert exc_info.value.retryable is True

    def test_malformed_api_response_raises_non_retryable_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        # choices フィールドが欠損した応答
        broken_mock = MagicMock()
        broken_mock.__enter__ = MagicMock(return_value=broken_mock)
        broken_mock.__exit__ = MagicMock(return_value=False)
        broken_mock.read.return_value = json.dumps({"error": "no choices"}).encode()

        provider = GenericApiLLMProvider(_config(max_retries=0))
        with patch("urllib.request.urlopen", return_value=broken_mock):
            with pytest.raises(LLMProviderError) as exc_info:
                provider.generate_draft(_draft_input())
        assert exc_info.value.retryable is False

    def test_retries_on_5xx_up_to_max_retries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import urllib.error

        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        call_count = 0

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            raise urllib.error.HTTPError(
                "https://api.example.test", 503, "Service Unavailable", {}, None
            )

        provider = GenericApiLLMProvider(_config(max_retries=2))
        with patch("urllib.request.urlopen", side_effect=side_effect):
            with pytest.raises(LLMProviderError):
                provider.generate_draft(_draft_input())
        # max_retries=2: 初回 1 + リトライ 2 = 計 3 回
        assert call_count == 3

    def test_retries_and_succeeds_on_second_attempt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import urllib.error

        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        call_count = 0

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise urllib.error.HTTPError(
                    "https://api.example.test", 503, "Service Unavailable", {}, None
                )
            return _mock_urlopen(_valid_content())

        provider = GenericApiLLMProvider(_config(max_retries=2))
        with patch("urllib.request.urlopen", side_effect=side_effect):
            result = provider.generate_draft(_draft_input())
        assert call_count == 2
        assert result.title != ""

    def test_no_retry_on_4xx(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import urllib.error

        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        call_count = 0

        def side_effect(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            raise urllib.error.HTTPError("https://api.example.test", 400, "Bad Request", {}, None)

        provider = GenericApiLLMProvider(_config(max_retries=3))
        with patch("urllib.request.urlopen", side_effect=side_effect):
            with pytest.raises(LLMProviderError):
                provider.generate_draft(_draft_input())
        # 4xx は retryable=False → 1 回のみ
        assert call_count == 1


# ---------------------------------------------------------------------------
# build_llm_provider integration
# ---------------------------------------------------------------------------


class TestBuildLLMProvider:
    def test_build_selects_generic_api_provider(self) -> None:
        provider = build_llm_provider(_config())
        assert isinstance(provider, GenericApiLLMProvider)

    def test_build_passes_config_to_provider(self) -> None:
        cfg = _config(model="claude-opus-4", provider_name="anthropic-api")
        provider = build_llm_provider(cfg)
        assert isinstance(provider, GenericApiLLMProvider)
        assert provider.get_provider_metadata().model == "claude-opus-4"
        assert provider.get_provider_metadata().provider_name == "anthropic-api"


# ---------------------------------------------------------------------------
# edge cases：advisory がシーケンス形式 / 設定不整合
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_generate_draft_raises_when_auth_env_var_not_configured(self) -> None:
        """auth_env_var=None のまま generate_draft を直接呼んだ場合。"""
        from spautopost.llm import LLMProviderConfigError as ConfigError

        provider = GenericApiLLMProvider(_config(auth_env_var=None))
        with pytest.raises(ConfigError):
            provider.generate_draft(_draft_input())

    def test_sequence_advisory_is_filtered_to_allowed_fields(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """advisory がリスト形式のとき先頭要素の許可フィールドのみ送信される。"""
        monkeypatch.setenv("LLM_API_KEY", "sk-test")
        captured_bodies: list[str] = []

        def mock_urlopen(req: object, timeout: object) -> MagicMock:
            import urllib.request as ureq

            if isinstance(req, ureq.Request) and req.data:
                captured_bodies.append(req.data.decode("utf-8"))
            return _mock_urlopen(_valid_content())

        seq_input = DraftInput(
            advisory=[
                {
                    "title": "Sequence Advisory",
                    "summary": "Seq summary.",
                    "internal_host": "10.0.0.1",  # 禁止フィールド
                },
                {"title": "Second (ignored)"},
            ],
            target_audience="mixed",
            target_language="ja-JP",
            urgency="normal",
            template_id="t1",
            prompt_version="v1",
            references=(),
        )
        provider = GenericApiLLMProvider(_config())
        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            provider.generate_draft(seq_input)

        assert captured_bodies
        assert "internal_host" not in captured_bodies[0]
        assert "10.0.0.1" not in captured_bodies[0]
        assert "Sequence Advisory" in captured_bodies[0]
