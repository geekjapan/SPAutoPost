"""OpenAI-compatible API を設定で有効化する generic_api provider。

非公式 UI 自動操作・ブラウザ scraping は本 adapter の対象外。
公式 REST API エンドポイント（/v1/chat/completions 互換）のみ対象。
認証情報（Bearer token）はコード・ログ・例外メッセージに出力しない。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from typing import Any

from spautopost.config import LLMConfig
from spautopost.llm import (
    DraftInput,
    DraftOutput,
    LLMProviderConfigError,
    LLMProviderError,
    ProviderMetadata,
    ProviderStatus,
)
from spautopost.secrets import is_secret_ref, secret_env_name

# ---------------------------------------------------------------------------
# System prompt（安全性ガイドライン・出力 JSON schema を含む）
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
あなたは社内セキュリティ担当者として、SharePoint お知らせ掲示板向け原稿を作成します。

安全性ガイドライン（必ず遵守）:
- 出典にない事実を断定しない
- 攻撃手順・PoC・脆弱性の悪用詳細を含めない
- 不確実な点は不確実と表現する
- 社内ネットワーク構成・認証情報・未公開情報を含めない

以下の JSON 形式のみで回答してください（余分なテキストなし）:
{
  "title": "タイトル（urgency に応じた接頭辞付き）",
  "summary_for_users": "一般利用者向け説明（1〜2文）",
  "impact": "影響範囲の説明",
  "required_actions": ["必要なアクション"],
  "references": [{"title": "参考", "url": "https://..."}],
  "admin_actions": ["管理者向けアクション"],
  "deadline": "対応期限（不明な場合は null）",
  "warnings": ["レビュアー向け警告"],
  "uncertainty_notes": ["不確実な点"]
}
"""

# advisory / reference フィールドの送信許可リスト（禁止情報を除外するため明示）
_ALLOWED_REFERENCE_FIELDS = frozenset({"title", "url"})

_ALLOWED_ADVISORY_FIELDS = frozenset(
    {
        "title",
        "summary",
        "description",
        "cvss_score",
        "cvss_vector",
        "severity",
        "cve_id",
        "jvn_id",
        "affected_products",
        "patch_available",
        "exploit_status",
        "workaround",
        "mitigation",
        "solution",
        "remediation",
        "deadline",
        "due_date",
        "recommended_deadline",
        "references",
    }
)


class GenericApiLLMProvider:
    """OpenAI-compatible REST API を設定で有効化する generic_api provider。

    設定項目:
    - endpoint_url: API エンドポイント URL
    - model: モデル ID（例: gpt-4o）
    - auth_env_var: Bearer token を格納する環境変数名
    - timeout_seconds: HTTP タイムアウト秒数（default 30）
    - max_retries: retryable エラー時の最大再試行回数（default 3）

    非対象:
    - ブラウザ UI 自動操作（Selenium・Playwright 等）
    - 非公式 API・reverse-engineered エンドポイント
    - Web scraping
    """

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._metadata = ProviderMetadata(
            provider_name=config.provider_name or "generic-api",
            provider_type="generic_api",
            model=config.model,
            prompt_version=config.prompt_version,
        )

    # ------------------------------------------------------------------
    # LLMProvider protocol
    # ------------------------------------------------------------------

    def validate_config(self) -> ProviderStatus:
        """設定の構造的正当性を確認する（実 API 呼び出しなし）。"""
        issues: list[str] = []
        endpoint = self._config.endpoint_url
        if not endpoint:
            issues.append("llm.endpoint_url is required for generic_api provider")
        else:
            if is_secret_ref(endpoint):
                env_name = secret_env_name(endpoint)
                endpoint = os.environ.get(env_name, "")
                if not endpoint:
                    issues.append(f"llm.endpoint_url env var {env_name!r} is not set")
            if endpoint and not endpoint.startswith("https://"):
                issues.append(
                    "llm.endpoint_url must use https:// to protect Bearer token in transit"
                )
        if not self._config.model:
            issues.append("llm.model is required for generic_api provider")
        if not self._config.auth_env_var:
            issues.append("llm.auth_env_var is required for generic_api provider")
        return ProviderStatus(
            valid=len(issues) == 0,
            issues=tuple(issues),
            metadata=self._metadata,
        )

    def generate_draft(self, draft_input: DraftInput) -> DraftOutput:
        """DraftInput を LLM API に送信して DraftOutput を返す。"""
        auth_env_var = self._config.auth_env_var
        if not auth_env_var:
            raise LLMProviderConfigError("llm.auth_env_var is not configured")
        token = os.environ.get(auth_env_var, "")
        if not token:
            # env var 名のみ出力（値は出力しない）
            raise LLMProviderError(
                f"env var {auth_env_var!r} is not set or empty",
                is_retryable=False,
            )
        return self._call_with_retry(draft_input, token)

    def get_provider_metadata(self) -> ProviderMetadata:
        return self._metadata

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    def _call_with_retry(self, draft_input: DraftInput, token: str) -> DraftOutput:
        import time

        for attempt in range(self._config.max_retries + 1):
            try:
                return self._attempt(draft_input, token)
            except LLMProviderError as exc:
                if not exc.is_retryable or attempt >= self._config.max_retries:
                    raise
                time.sleep(1)
        # max_retries >= 0 保証（config validation 済み）かつ retryable=True の場合、
        # ループ内で必ず raise されるためここには到達しない
        raise AssertionError("unreachable")

    def _attempt(self, draft_input: DraftInput, token: str) -> DraftOutput:
        payload = _build_payload(self._config.model or "", draft_input)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        endpoint = self._config.endpoint_url or ""
        if is_secret_ref(endpoint):
            env_name = secret_env_name(endpoint)
            endpoint = os.environ.get(env_name, "")
            if not endpoint:
                raise LLMProviderError(
                    f"env var {env_name!r} referenced by llm.endpoint_url is not set",
                    is_retryable=False,
                )
        req = urllib.request.Request(  # noqa: S310
            endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                # Bearer token はリクエスト時のみ使用し、変数の寿命を最小化
                "Authorization": f"Bearer {token}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:  # noqa: S310
                body = resp.read()
        except urllib.error.HTTPError as exc:
            retryable = exc.code >= 500 or exc.code == 429
            raise LLMProviderError(
                f"HTTP {exc.code} from LLM API",
                is_retryable=retryable,
            ) from exc
        except TimeoutError as exc:
            raise LLMProviderError(
                f"timeout calling LLM API: {exc}",
                is_retryable=True,
            ) from exc
        except (urllib.error.URLError, OSError) as exc:
            raise LLMProviderError(
                f"network error calling LLM API: {exc}",
                is_retryable=True,
            ) from exc
        except ValueError as exc:
            raise LLMProviderError(
                f"invalid request or URL: {exc}",
                is_retryable=False,
            ) from exc
        return _parse_body(body, draft_input)


# ---------------------------------------------------------------------------
# request / response helpers（副作用なし、モジュールレベルで分離）
# ---------------------------------------------------------------------------


def _build_payload(model: str, draft_input: DraftInput) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(draft_input)},
        ],
    }


def _build_user_message(draft_input: DraftInput) -> str:
    """DraftInput を LLM ユーザーメッセージに変換する。Secret・PII を含めない。"""
    advisory_safe = _safe_advisory(draft_input.advisory)
    refs_safe = _safe_references(draft_input.references)
    lines = [
        f"urgency: {draft_input.urgency}",
        f"target_audience: {draft_input.target_audience}",
        f"target_language: {draft_input.target_language}",
        f"template_id: {draft_input.template_id}",
        f"prompt_version: {draft_input.prompt_version}",
        "",
        "advisory:",
        json.dumps(advisory_safe, ensure_ascii=False, indent=2),
        "",
        "references:",
        json.dumps(refs_safe, ensure_ascii=False, indent=2),
    ]
    return "\n".join(lines)


def _safe_references(refs: object) -> list[dict[str, str]]:
    """references から title・url のみ抽出する（内部 URL 等の禁止情報を除外）。"""
    if not isinstance(refs, Sequence) or isinstance(refs, str | bytes | bytearray):
        return []
    result: list[dict[str, str]] = []
    for ref in refs:
        if isinstance(ref, Mapping):
            safe = {k: str(v) for k, v in ref.items() if k in _ALLOWED_REFERENCE_FIELDS}
            if safe:
                result.append(safe)
    return result


def _safe_advisory(advisory: object) -> dict[str, object]:
    """advisory から送信許可フィールドのみ抽出する（禁止情報を除外）。"""
    if isinstance(advisory, Mapping):
        filtered: dict[str, object] = {
            k: v for k, v in advisory.items() if k in _ALLOWED_ADVISORY_FIELDS
        }
        if "references" in filtered:
            filtered["references"] = _safe_references(filtered["references"])
        return filtered
    if isinstance(advisory, Sequence) and not isinstance(advisory, str | bytes | bytearray):
        first = next(iter(advisory), None)
        if isinstance(first, Mapping):
            filtered = {k: v for k, v in first.items() if k in _ALLOWED_ADVISORY_FIELDS}
            if "references" in filtered:
                filtered["references"] = _safe_references(filtered["references"])
            return filtered
    return {}


_REQUIRED_DRAFT_FIELDS = frozenset({"title", "summary_for_users", "impact"})
_REQUIRED_SEQUENCE_FIELDS = frozenset({"required_actions"})


def _validate_draft_fields(data: dict[str, Any]) -> None:
    missing = [f for f in _REQUIRED_DRAFT_FIELDS if f not in data or data[f] is None]
    # required_actions must be a list/sequence so _build_draft_output._seq() can use it
    bad_type = [
        f
        for f in _REQUIRED_SEQUENCE_FIELDS
        if f not in data
        or data[f] is None
        or isinstance(data[f], str | bytes | bytearray)
        or not isinstance(data[f], Sequence)
    ]
    if missing or bad_type:
        raise LLMProviderError(
            f"LLM response missing or invalid required fields: {sorted(missing + bad_type)}",
            is_retryable=False,
        )


def _parse_body(body: bytes, draft_input: DraftInput) -> DraftOutput:
    """API レスポンス body を DraftOutput に変換する。"""
    try:
        api_resp = json.loads(body)
        content = api_resp["choices"][0]["message"]["content"]
        output_data = json.loads(content)
        if not isinstance(output_data, dict):
            raise TypeError("parsed content is not a JSON object")
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise LLMProviderError(
            f"failed to parse LLM API response: {type(exc).__name__}",
            is_retryable=False,
        ) from None
    _validate_draft_fields(output_data)
    return _build_draft_output(output_data, draft_input)


def _build_draft_output(data: dict[str, Any], draft_input: DraftInput) -> DraftOutput:
    from spautopost.llm.templates import _input_hash  # local import to avoid circular dep

    def _seq(key: str) -> tuple[Any, ...]:
        val = data.get(key, ())
        if isinstance(val, Sequence) and not isinstance(val, str | bytes | bytearray):
            return tuple(val)
        return ()

    return DraftOutput(
        title=str(data.get("title", "（タイトル未生成）")),
        summary_for_users=str(data.get("summary_for_users", "")),
        impact=str(data.get("impact", "")),
        required_actions=_seq("required_actions"),
        references=_seq("references") or tuple(draft_input.references),
        warnings=_seq("warnings"),
        admin_actions=_seq("admin_actions"),
        deadline=data.get("deadline") if isinstance(data.get("deadline"), str) else None,
        uncertainty_notes=_seq("uncertainty_notes"),
        source_mapping={
            "provider_type": "generic_api",
            "prompt_version": draft_input.prompt_version,
        },
        validation_hints=(
            "guardrail:no_unsupported_claims",
            "guardrail:no_attack_steps_or_poc",
            "human_review_required",
        ),
        generation_input_hash=_input_hash(draft_input),
    )


__all__ = ["GenericApiLLMProvider", "LLMProviderError"]
