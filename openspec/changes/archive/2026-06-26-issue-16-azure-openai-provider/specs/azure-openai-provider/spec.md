# Spec: azure-openai-provider

## Purpose

Azure OpenAI / Microsoft Foundry provider adapter の実装要件を定義する。`LLMProvider` interface を実装し、`DraftInput → DraftOutput` の変換を Chat Completions API 経由で行う。Secret はコード・ログ・fixture に含めず、監査 metadata を完全に記録する。

## ADDED Requirements

### Requirement: AzureOpenAIProvider が LLMProvider interface を実装する

`AzureOpenAIProvider` は `validate_config`・`generate_draft`・`get_provider_metadata` の 3 メソッドを実装しなければならない（SHALL）。`provider_type` は `"production_api"` とする。

#### Scenario: provider が interface を満たす

- **WHEN** `AzureOpenAIProvider` のインスタンスを `isinstance(p, LLMProvider)` で検査する
- **THEN** `True` を返すこと

#### Scenario: validate_config が設定不備を検出する

- **WHEN** endpoint または deployment が空の設定で `validate_config` を呼ぶ
- **THEN** `ProviderStatus(valid=False, issues=[...])` を返し、Secret 値を issues に含めないこと

### Requirement: DraftInput を Chat Completions API に変換して DraftOutput を返す

`generate_draft` は `DraftInput` を受け取り、Azure OpenAI Chat Completions API（`{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}`）を呼び出して `DraftOutput` を返さなければならない（SHALL）。

#### Scenario: API 呼び出しが成功する

- **WHEN** API がステータス 200 と正常な JSON を返す
- **THEN** `DraftOutput` が返り、`generation_input_hash` が設定されていること

#### Scenario: レスポンスの JSON が不正の場合

- **WHEN** API がステータス 200 を返すが JSON が `DraftOutput` に変換できない形式である
- **THEN** `LLMProviderError` を送出し、`is_retryable=False` であること

### Requirement: API key は環境変数経由でのみ参照する

`AzureOpenAIProvider` は API key をコード・設定ファイル・テスト fixture に直書きしてはならない（SHALL NOT）。config の `azure.api_key` は `env:AZURE_OPENAI_API_KEY` 形式のシークレット参照でなければならず（SHALL）、呼び出し時に `os.environ` から解決する。

#### Scenario: API key が環境変数から解決される

- **WHEN** `env:AZURE_OPENAI_API_KEY` 参照を持つ config で `AzureOpenAIProvider` が HTTP リクエストを組み立てる
- **THEN** `api-key` ヘッダに環境変数の値が設定され、config の参照文字列（`env:...`）は送られないこと

#### Scenario: API key 環境変数が未設定の場合

- **WHEN** `AZURE_OPENAI_API_KEY` 環境変数が未設定の状態で `generate_draft` を呼ぶ
- **THEN** `LLMProviderError` を送出し、エラーメッセージに Secret 値を含めないこと

#### Scenario: API key がログ・例外メッセージに漏洩しない

- **WHEN** API 呼び出しが失敗し例外を送出する
- **THEN** 例外メッセージおよびログに API key の値が含まれないこと

### Requirement: タイムアウトとリトライを実装する

`generate_draft` は設定された `timeout_secs` でリクエストを打ち切り、`max_retries` 回まで指数バックオフでリトライしなければならない（SHALL）。rate limit（HTTP 429）・サーバーエラー（HTTP 5xx）・タイムアウトはリトライ対象とする。認証エラー（HTTP 401/403）・リクエスト不正（HTTP 400）はリトライしない。

#### Scenario: タイムアウト時にリトライする

- **WHEN** HTTP リクエストがタイムアウトし、残りリトライ回数がある
- **THEN** 指数バックオフで再試行し、最終的に成功した場合 `DraftOutput` を返すこと

#### Scenario: max_retries を超えた場合

- **WHEN** タイムアウトまたは 5xx が max_retries 回を超えて続く
- **THEN** `LLMProviderError(is_retryable=True)` を送出すること

#### Scenario: 認証エラーはリトライしない

- **WHEN** API が HTTP 401 を返す
- **THEN** 即座に `LLMProviderError(is_retryable=False)` を送出すること

### Requirement: 監査 metadata を DraftOutput に付与する

`generate_draft` 成功時には以下の監査 metadata を `DraftOutput` に含めなければならない（SHALL）:

- `generation_input_hash`: `SHA-256(canonical_json(DraftInput))` 16 進数文字列
- `source_mapping["provider_name"]`: `"azure-openai"`
- `source_mapping["model"]`: 使用した deployment/model 名
- `source_mapping["prompt_version"]`: config の `prompt_version`
- `source_mapping["token_usage"]`: `{"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}` （取得可能な場合）

API key・authorization header は `source_mapping` または `DraftOutput` に含めてはならない（SHALL NOT）。

#### Scenario: 成功時に監査 metadata が付与される

- **WHEN** `generate_draft` が正常に `DraftOutput` を返す
- **THEN** `generation_input_hash` が設定され、`source_mapping` に `provider_name`・`model`・`prompt_version` が含まれること

#### Scenario: 監査 metadata に Secret が含まれない

- **WHEN** `DraftOutput` の `source_mapping` を確認する
- **THEN** API key・authorization header が含まれていないこと

### Requirement: 構造化 JSON 出力を要求する

`generate_draft` は Chat Completions API のリクエストに `response_format: {"type": "json_object"}` を指定し、`DraftOutput` フィールドを JSON で返すよう system prompt を設定しなければならない（SHALL）。返却 JSON が必須フィールド（`title` / `summary_for_users` / `impact` / `required_actions` / `references`）を欠く場合、`LLMProviderError` を送出する。

#### Scenario: 必須フィールドを含む JSON を受信した場合

- **WHEN** API が title・summary_for_users・impact・required_actions・references を含む JSON を返す
- **THEN** `DraftOutput` に正しくマッピングされること

#### Scenario: 必須フィールドが欠損した JSON を受信した場合

- **WHEN** API が title を欠く JSON を返す
- **THEN** `LLMProviderError(is_retryable=False)` を送出すること

### Requirement: production_approved フラグによる起動時ガード

`production_api` provider は `llm.production_approved: true` が設定されていない場合、`validate_config` が `valid=False` を返し `generate_draft` を開始してはならない（SHALL）。

#### Scenario: production_approved が false の場合に generate_draft を拒否する

- **WHEN** `llm.production_approved: false` の config で `AzureOpenAIProvider.validate_config` を呼ぶ
- **THEN** `ProviderStatus(valid=False, issues=["production_approved フラグが true でない"])` を返すこと

#### Scenario: production_approved が true の場合に validate_config が成功する

- **WHEN** 必須フィールドがすべて設定され `llm.production_approved: true` の config で `validate_config` を呼ぶ
- **THEN** `ProviderStatus(valid=True, issues=())` を返すこと
