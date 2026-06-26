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
    ProviderMetadata,
    ProviderStatus,
)

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

# advisory フィールドの送信許可リスト（禁止情報を除外するため明示）
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


class LLMProviderError(Exception):
    """LLM API 呼び出しの失敗。Secret 値はメッセージに含めない。"""

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


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
        if not self._config.endpoint_url:
            issues.append("llm.endpoint_url is required for generic_api provider")
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
                retryable=False,
            )
        return self._call_with_retry(draft_input, token)

    def get_provider_metadata(self) -> ProviderMetadata:
        return self._metadata

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    def _call_with_retry(self, draft_input: DraftInput, token: str) -> DraftOutput:
        last_error: LLMProviderError | None = None
        for attempt in range(self._config.max_retries + 1):
            try:
                return self._attempt(draft_input, token)
            except LLMProviderError as exc:
                last_error = exc
                if not exc.retryable or attempt >= self._config.max_retries:
                    raise
        raise last_error  # type: ignore[misc]

    def _attempt(self, draft_input: DraftInput, token: str) -> DraftOutput:
        payload = _build_payload(self._config.model or "", draft_input)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        endpoint = self._config.endpoint_url or ""
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
            retryable = exc.code >= 500
            raise LLMProviderError(
                f"HTTP {exc.code} from LLM API",
                retryable=retryable,
            ) from exc
        except urllib.error.URLError as exc:
            raise LLMProviderError(
                f"network error calling LLM API: {exc.reason}",
                retryable=True,
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
        json.dumps(list(draft_input.references), ensure_ascii=False, indent=2),
    ]
    return "\n".join(lines)


def _safe_advisory(advisory: object) -> dict[str, object]:
    """advisory から送信許可フィールドのみ抽出する（禁止情報を除外）。"""
    if isinstance(advisory, Mapping):
        return {k: v for k, v in advisory.items() if k in _ALLOWED_ADVISORY_FIELDS}
    if isinstance(advisory, Sequence) and not isinstance(advisory, str | bytes | bytearray):
        first = next(iter(advisory), None)
        if isinstance(first, Mapping):
            return {k: v for k, v in first.items() if k in _ALLOWED_ADVISORY_FIELDS}
    return {}


def _parse_body(body: bytes, draft_input: DraftInput) -> DraftOutput:
    """API レスポンス body を DraftOutput に変換する。"""
    try:
        api_resp = json.loads(body)
        content = api_resp["choices"][0]["message"]["content"]
        output_data: dict[str, Any] = json.loads(content)
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise LLMProviderError(
            f"failed to parse LLM API response: {exc}",
            retryable=False,
        ) from exc
    return _build_draft_output(output_data, draft_input)


def _build_draft_output(data: dict[str, Any], draft_input: DraftInput) -> DraftOutput:
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
    )


__all__ = ["GenericApiLLMProvider", "LLMProviderError"]
