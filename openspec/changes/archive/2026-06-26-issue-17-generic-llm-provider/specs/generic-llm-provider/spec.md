# Spec: generic-llm-provider

## Purpose

OpenAI-compatible REST API を設定駆動で呼び出す `generic_api` provider adapter の要件を定義する。

## ADDED Requirements

### Requirement: generic_api provider を設定で有効化できる

`llm.provider = "generic_api"` を設定した場合、システムは `GenericApiLLMProvider` を構築しなければならない（SHALL）。

`LLMConfig` には以下のフィールドを追加する：
- `endpoint_url: str | None` — API endpoint URL（`env:VAR` 参照可）
- `model: str | None` — モデル ID（例: `gpt-4o`）
- `auth_env_var: str | None` — Bearer token を取得する環境変数名
- `timeout_seconds: int` — HTTP タイムアウト秒数（default 30）
- `max_retries: int` — 最大リトライ回数（default 3）

#### Scenario: generic_api provider が構築される

- **WHEN** `LLMConfig(provider="generic_api", endpoint_url=..., model=..., auth_env_var=...)` で `build_llm_provider` を呼ぶ
- **THEN** `GenericApiLLMProvider` インスタンスが返される

#### Scenario: validate_config が設定の構造的正当性を確認する

- **WHEN** `endpoint_url` が None または空文字列のまま `validate_config()` を呼ぶ
- **THEN** `valid=False` と問題のリストを含む `ProviderStatus` が返される

### Requirement: request は DraftInput から OpenAI-compatible メッセージに変換する

システムは `DraftInput` を OpenAI-compatible な `POST /v1/chat/completions` リクエストに変換しなければならない（SHALL）。

変換仕様：
- `system` メッセージ：セキュリティ担当者役割・安全性ガイドライン・フォーマット指示
- `user` メッセージ：advisory 概要・urgency・target_audience・target_language・references

LLM に送信してはならない情報（SHALL NOT）：
- API key / auth header 値
- 個人情報（PII）
- 社内ネットワーク構成
- 未公開インシデント情報

#### Scenario: DraftInput がリクエストに変換される

- **WHEN** `generate_draft(draft_input)` を呼ぶ
- **THEN** OpenAI-compatible JSON payload（`model`, `messages`）が生成される

#### Scenario: 禁止情報がリクエストに含まれない

- **WHEN** リクエスト payload を検査する
- **THEN** auth header 値・API key が `messages` の内容に含まれていない

### Requirement: response を DraftOutput にマッピングする

システムは API レスポンスの `choices[0].message.content` を `DraftOutput` にマッピングしなければならない（SHALL）。

マッピングが失敗した場合（JSON 解析エラー・必須フィールド欠損・非 2xx HTTP）は `LLMProviderError` を送出する。

#### Scenario: JSON 形式の応答が DraftOutput に変換される

- **WHEN** API が有効な `choices[0].message.content` を返す
- **THEN** `DraftOutput` が構築され返される

#### Scenario: 非 2xx レスポンスが LLMProviderError になる

- **WHEN** API が 4xx / 5xx を返す
- **THEN** `LLMProviderError` が送出され、auth header 値はメッセージに含まれない

### Requirement: タイムアウトとリトライを実装する

システムはタイムアウトと retryable エラーへのリトライを実装しなければならない（SHALL）。

- タイムアウト：`timeout_seconds` 設定値（default 30 秒）
- リトライ：`max_retries` 設定値（default 3 回）
- リトライ対象：タイムアウト・一時的ネットワークエラー・5xx（`retryable=True`）
- リトライ非対象：4xx（`retryable=False`）・response 解析失敗

#### Scenario: タイムアウトで LLMProviderError が送出される

- **WHEN** API 呼び出しが timeout_seconds を超過する
- **THEN** `LLMProviderError(retryable=True)` が送出される

#### Scenario: 5xx でリトライされる

- **WHEN** API が 5xx を返す
- **THEN** `max_retries` 回まで再試行し、最終的に `LLMProviderError` が送出される

### Requirement: provider metadata を監査ログ用に提供する

システムは `get_provider_metadata()` で監査に必要なメタデータを返さなければならない（SHALL）。

必須フィールド：
- `provider_name`（設定値、または "generic-api"）
- `provider_type`（`"generic_api"`）
- `model`（設定値）
- `prompt_version`（設定値）

Secret（auth header 値）は `ProviderMetadata` に含めてはならない（SHALL NOT）。

#### Scenario: ProviderMetadata に Secret が含まれない

- **WHEN** `get_provider_metadata()` を呼ぶ
- **THEN** 返り値に API key・auth header 値が含まれていない

### Requirement: 非公式 API・UI 自動操作は generic_api adapter の対象外とする

`generic_api` adapter は公式 API エンドポイントのみを対象とする（SHALL）。

以下は本 adapter の対象外であり、実装してはならない（SHALL NOT）：
- ブラウザ UI の自動操作（Selenium・Playwright 等）
- reverse-engineered または非公式エンドポイントの呼び出し
- Web scraping による結果取得

#### Scenario: 非公式 API 利用の排除が明記されている

- **WHEN** `generic_provider.py` の docstring または設計ドキュメントを参照する
- **THEN** 非公式 UI 自動操作が対象外と明記されている
