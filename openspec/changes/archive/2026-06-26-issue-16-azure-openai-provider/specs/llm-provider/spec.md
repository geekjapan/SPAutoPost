# Spec: llm-provider (delta for issue-16)

## Purpose

`build_llm_provider` が `production_api` を選択した場合に `AzureOpenAIProvider` を返すよう拡張し、`production_approved` フラグを config スキーマに追加する。

## ADDED Requirements

### Requirement: build_llm_provider が production_api を選択する

`build_llm_provider` は `config.llm.provider == "production_api"` の場合、`AzureOpenAIProvider` を構築して返さなければならない（SHALL）。azure サブセクション（`endpoint` / `deployment` / `api_version` / `auth_type` / `timeout_secs` / `max_retries` / `production_approved`）は `LLMConfig` を経由して `AzureOpenAIProvider` に渡す。

#### Scenario: production_api が選択された場合に AzureOpenAIProvider が返る

- **WHEN** `LLMConfig(provider="production_api", ...)` で `build_llm_provider` を呼ぶ
- **THEN** `AzureOpenAIProvider` のインスタンスが返ること

### Requirement: llm.azure サブセクションの config 検証

config の `llm.azure` サブセクションは以下のフィールドを持つ。`provider == "production_api"` の場合、`endpoint`・`deployment` は必須とする（SHALL）。

| フィールド | 型 | 説明 |
|---|---|---|
| `endpoint` | string | `https://{resource}.openai.azure.com` 形式 |
| `deployment` | string | deployment name または model alias |
| `api_version` | string | API version（省略時 `2024-02-01`） |
| `auth_type` | `api_key` \| `managed_identity` | 認証方式（省略時 `api_key`） |
| `api_key` | secret ref | `env:AZURE_OPENAI_API_KEY`（`auth_type=api_key` 時必須） |
| `timeout_secs` | int | タイムアウト秒数（省略時 60） |
| `max_retries` | int | 最大リトライ回数（省略時 3） |
| `production_approved` | bool | 情報セキュリティ部門承認フラグ（省略時 `false`） |

#### Scenario: production_api provider で endpoint が未設定の場合

- **WHEN** `llm.provider: production_api` で `llm.azure.endpoint` が未設定の config を検証する
- **THEN** `ConfigValidationError` が送出されること

#### Scenario: llm.azure の設定が正常に検証される

- **WHEN** `endpoint`・`deployment`・`production_approved: true` を設定した config を検証する
- **THEN** 検証が成功し `LLMConfig` が構築されること

## MODIFIED Requirements

### Requirement: Provider interface definition

Provider は以下の interface を実装しなければならない（SHALL）。この interface は M1 で確定版とし、mock provider (#6) の実装基準とする。M3 では `AzureOpenAIProvider` がこの interface を実装する。

```text
Provider.validate_config() -> ProviderStatus
Provider.generate_draft(input: DraftInput) -> DraftOutput
Provider.get_provider_metadata() -> ProviderMetadata
Provider.estimate_cost(input: DraftInput) -> CostEstimate | None  # optional
```

`ProviderMetadata` には以下を含めること:
- `provider_name: str`
- `provider_type: "production_api" | "production_flow" | "generic_api" | "test_mock" | "test_manual"`
- `model: str | None`
- `prompt_version: str | None`

#### Scenario: mock provider が interface を実装する

- **WHEN** mock provider (#6) を実装する
- **THEN** `generate_draft`・`validate_config`・`get_provider_metadata` の 3 メソッドが実装されていること

#### Scenario: AzureOpenAIProvider が interface を実装する

- **WHEN** `AzureOpenAIProvider` のインスタンスを確認する
- **THEN** `generate_draft`・`validate_config`・`get_provider_metadata` の 3 メソッドが実装されていること

#### Scenario: test_manual provider が interface を実装する

- **WHEN** test_manual 結果を DraftPost に手動取込する
- **THEN** `provider_type = "test_manual"` として audit log に記録されること
