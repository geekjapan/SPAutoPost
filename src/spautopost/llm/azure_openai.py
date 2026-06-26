"""Azure OpenAI / Foundry provider adapter。

HTTP は stdlib urllib を使用し、新規ランタイム依存を追加しない。
API key は env: 参照で解決し、コード・ログ・fixture に漏洩させない。
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any

from spautopost.config import AzureOpenAIConfig
from spautopost.secrets import is_secret_ref, secret_env_name

from . import (
    DraftInput,
    DraftOutput,
    LLMProviderError,
    ProviderMetadata,
    ProviderStatus,
)
from .templates import _input_hash as _compute_input_hash

_SYSTEM_PROMPT = (  # noqa: E501
    "あなたは社内セキュリティ担当者として、SharePoint お知らせ掲示板向け原稿を JSON 形式で作成します。\n"  # noqa: E501
    "以下の JSON スキーマに従って出力してください。\n\n"
    "{\n"
    '  "title": "記事タイトル（緊急度: emergency=[緊急] high=[重要] normal=[注意喚起] low=[参考]）",\n'  # noqa: E501
    '  "summary_for_users": "一般利用者向けの要約（200文字以内）",\n'
    '  "impact": "影響範囲の説明",\n'
    '  "required_actions": ["利用者向けアクション1", "利用者向けアクション2"],\n'
    '  "admin_actions": ["管理者向けアクション1"],\n'
    '  "deadline": "対応期限（ISO 8601 または null）",\n'
    '  "references": [{"title": "参考リンクタイトル", "url": "https://..."}],\n'
    '  "warnings": ["レビュー担当者への注意事項"],\n'
    '  "uncertainty_notes": ["不確実な点"],\n'
    '  "validation_hints": ["guardrail:no_unsupported_claims",'
    ' "guardrail:no_attack_steps_or_poc", "human_review_required"]\n'
    "}\n\n"
    "Safety rules:\n"
    "- PoC、攻撃手順、悪用コードを含めない\n"
    "- 出典にない事実を断定しない（不確実な点は uncertainty_notes に記録する）\n"
    "- validation_hints には guardrail:no_unsupported_claims,"
    " guardrail:no_attack_steps_or_poc, human_review_required を含める\n"
    "- 緊急度 urgency の値に従って title のプレフィックスを決定する\n"
)

_REQUIRED_OUTPUT_FIELDS = (
    "title",
    "summary_for_users",
    "impact",
    "required_actions",
    "references",
)


def _default_sleep(secs: float) -> None:
    time.sleep(secs)


class AzureOpenAIProvider:
    """Azure OpenAI / Foundry LLM provider。production_api 分類。"""

    def __init__(
        self,
        config: AzureOpenAIConfig,
        prompt_version: str | None = None,
        *,
        _sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self._config = config
        self._prompt_version = prompt_version
        self._sleep_fn: Callable[[float], None] = _sleep_fn or _default_sleep
        self._metadata = ProviderMetadata(
            provider_name="azure-openai",
            provider_type="production_api",
            model=config.deployment or None,
            prompt_version=prompt_version,
        )

    def validate_config(self) -> ProviderStatus:
        issues: list[str] = []
        cfg = self._config
        if not cfg.production_approved:
            issues.append(
                "production_approved フラグが true でない（情報セキュリティ部門の承認が必要）"
            )
        if not cfg.endpoint:
            issues.append("llm.azure.endpoint が未設定")
        elif not cfg.endpoint.startswith("https://"):
            issues.append("llm.azure.endpoint は https:// で始まる必要があります")
        if not cfg.deployment:
            issues.append("llm.azure.deployment が未設定")
        if cfg.auth_type == "managed_identity":
            issues.append(
                "auth_type=managed_identity は未実装（M3 では api_key を使用してください）"
            )
        elif cfg.auth_type == "api_key":
            if not cfg.api_key_ref:
                issues.append(
                    "llm.azure.api_key が未設定（env:AZURE_OPENAI_API_KEY 形式で設定してください）"
                )
            elif not is_secret_ref(cfg.api_key_ref):
                issues.append(
                    "llm.azure.api_key は env:NAME 形式のシークレット参照を使用してください"
                    "（例: env:AZURE_OPENAI_API_KEY）。生の API キー文字列は設定できません。"
                )
        return ProviderStatus(
            valid=len(issues) == 0,
            issues=tuple(issues),
            metadata=self._metadata,
        )

    def generate_draft(self, draft_input: DraftInput) -> DraftOutput:
        status = self.validate_config()
        if not status.valid:
            raise LLMProviderError(
                f"provider config invalid: {'; '.join(status.issues)}",
                is_retryable=False,
            )
        api_key = self._resolve_api_key()
        input_hash = _compute_input_hash(draft_input)
        response_data = self._retry_loop(draft_input, api_key)
        return _parse_response(response_data, input_hash, self._metadata, self._prompt_version)

    def get_provider_metadata(self) -> ProviderMetadata:
        return self._metadata

    def _resolve_api_key(self) -> str:
        ref = self._config.api_key_ref or ""
        if is_secret_ref(ref):
            name = secret_env_name(ref)
            value = os.environ.get(name)
            if not value:
                raise LLMProviderError(
                    f"required secret env var is not set: {name}",
                    is_retryable=False,
                )
            return value
        if ref:
            raise LLMProviderError(
                "api_key_ref は env:NAME 形式で設定してください（生値は不可）",
                is_retryable=False,
            )
        raise LLMProviderError("api_key が設定されていない", is_retryable=False)

    def _retry_loop(self, draft_input: DraftInput, api_key: str) -> dict[str, Any]:
        cfg = self._config
        last_error: LLMProviderError | None = None
        for attempt in range(cfg.max_retries + 1):
            if attempt > 0:
                delay = float(2 ** (attempt - 1))
                self._sleep_fn(delay)
            try:
                return self._call_api(draft_input, api_key)
            except LLMProviderError as e:
                last_error = e
                if not e.is_retryable:
                    raise
        raise last_error or LLMProviderError("max retries exceeded", is_retryable=True)

    def _call_api(self, draft_input: DraftInput, api_key: str) -> dict[str, Any]:
        cfg = self._config
        url = (
            f"{cfg.endpoint.rstrip('/')}/openai/deployments/{cfg.deployment}"
            f"/chat/completions?api-version={cfg.api_version}"
        )
        body = _build_request_body(draft_input)
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "api-key": api_key,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=cfg.timeout_secs) as resp:  # noqa: S310
                raw = resp.read()
        except urllib.error.HTTPError as e:
            raise _map_http_error(e) from e
        except urllib.error.URLError as e:
            raise LLMProviderError(
                f"network error: {type(e.reason).__name__}", is_retryable=True
            ) from e
        except OSError as e:
            raise LLMProviderError(f"network error: {type(e).__name__}", is_retryable=True) from e

        try:
            result: dict[str, Any] = json.loads(raw)
            return result
        except json.JSONDecodeError as e:
            raise LLMProviderError(
                "failed to decode API response as JSON", is_retryable=False
            ) from e


def _map_http_error(e: urllib.error.HTTPError) -> LLMProviderError:
    code = e.code
    if code == 429:
        return LLMProviderError(f"rate limited (HTTP {code})", is_retryable=True)
    if 400 <= code < 500:
        return LLMProviderError(f"client error (HTTP {code})", is_retryable=False)
    return LLMProviderError(f"server error (HTTP {code})", is_retryable=True)


def _build_request_body(draft_input: DraftInput) -> dict[str, Any]:
    user_content = json.dumps(
        {
            "advisory": draft_input.advisory,
            "references": list(draft_input.references),
            "target_audience": draft_input.target_audience,
            "target_language": draft_input.target_language,
            "urgency": draft_input.urgency,
            "template_id": draft_input.template_id,
            "prompt_version": draft_input.prompt_version,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return {
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "response_format": {"type": "json_object"},
    }


def _parse_response(
    data: dict[str, Any],
    input_hash: str,
    metadata: ProviderMetadata,
    prompt_version: str | None,
) -> DraftOutput:
    try:
        content_str = data["choices"][0]["message"]["content"]
        content = json.loads(content_str)
        if not isinstance(content, dict):
            raise TypeError("content is not a JSON object")
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
        raise LLMProviderError(
            "failed to extract content from API response", is_retryable=False
        ) from e

    missing = [f for f in _REQUIRED_OUTPUT_FIELDS if f not in content]
    if missing:
        raise LLMProviderError(
            f"API response missing required fields: {missing}", is_retryable=False
        )

    usage: Mapping[str, Any] = {}
    try:
        usage = data.get("usage", {}) or {}
    except (TypeError, AttributeError):
        pass

    token_usage_str = json.dumps(
        {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }
    )

    source_mapping = {
        "provider_name": metadata.provider_name,
        "model": metadata.model or "",
        "prompt_version": prompt_version or "",
        "token_usage": token_usage_str,
    }

    raw_hints = content.get("validation_hints")
    validation_hints = tuple(str(h) for h in raw_hints) if isinstance(raw_hints, list) else ()
    # guardrail hints が欠ける場合に補完する
    required_hints = (
        "guardrail:no_unsupported_claims",
        "guardrail:no_attack_steps_or_poc",
        "human_review_required",
    )
    for hint in required_hints:
        if hint not in validation_hints:
            validation_hints = (*validation_hints, hint)

    raw_req_actions = content.get("required_actions")
    raw_admin_actions = content.get("admin_actions")
    raw_warnings = content.get("warnings")
    raw_notes = content.get("uncertainty_notes")
    raw_refs = content.get("references")

    return DraftOutput(
        title=str(content.get("title", "")),
        summary_for_users=str(content.get("summary_for_users", "")),
        impact=str(content.get("impact", "")),
        required_actions=(
            tuple(str(a) for a in raw_req_actions) if isinstance(raw_req_actions, list) else ()
        ),
        admin_actions=(
            tuple(str(a) for a in raw_admin_actions) if isinstance(raw_admin_actions, list) else ()
        ),
        deadline=content.get("deadline") or None,
        references=(
            tuple(dict(r) for r in raw_refs if isinstance(r, Mapping))
            if isinstance(raw_refs, list)
            else ()
        ),
        warnings=tuple(str(w) for w in raw_warnings) if isinstance(raw_warnings, list) else (),
        uncertainty_notes=tuple(str(n) for n in raw_notes) if isinstance(raw_notes, list) else (),
        validation_hints=validation_hints,
        source_mapping=source_mapping,
        generation_input_hash=input_hash,
    )
