## MODIFIED Requirements

### Requirement: production_api provider の利用条件

`production_api` provider（Microsoft Foundry / Azure OpenAI 等）を利用するシステムは、以下の条件を すべて 満たさなければならない（SHALL）。

1. API 利用が社内情報セキュリティ部門によって承認されている
2. 利用する API の規約上、業務データの投入が許可されている
3. Entra ID managed identity または組織が管理する API key で認証している
4. rate limit・タイムアウト・エラーハンドリングを実装している
5. 監査ログを取得または補完できる手段が確保されている

承認状態は設定ファイルで表現しなければならない（SHALL）。共通の承認源は `llm.production_approved: true` とする。`production_api` では Azure 固有設定の承認源として `llm.azure.production_approved: true` も起動時設定バリデーションで受け入れる。ただし、これは情報セキュリティ部門の承認取得を代替するものではなく、取得済み承認を設定で表現するためのフラグである。

#### Scenario: production_api provider が未承認の状態で使用される

- **WHEN** `llm.production_approved` と `llm.azure.production_approved` のどちらも `true` でない状態で production_api provider を使用しようとする
- **THEN** システムは起動時設定バリデーションでエラーを返し、生成処理を開始してはならない

#### Scenario: production_api provider が共通承認フラグで使用される

- **WHEN** `llm.production_approved: true` が設定され、必要な `llm.azure` サブセクションが揃っている
- **THEN** システムは承認ゲートを満たしたものとして起動時設定バリデーションを通過させる

#### Scenario: production_api provider が Azure 固有承認フラグで使用される

- **WHEN** `llm.azure.production_approved: true` が設定され、必要な `llm.azure` サブセクションが揃っている
- **THEN** システムは承認ゲートを満たしたものとして起動時設定バリデーションを通過させる

#### Scenario: production_api provider が適切に認証されている

- **WHEN** production_api provider が Entra ID managed identity で認証する
- **THEN** API key をコードまたは設定ファイルに直書きすることなく認証が完了すること

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
| `production_approved` | bool | Azure 固有の情報セキュリティ部門承認フラグ（省略時 `false`） |

#### Scenario: production_api provider で endpoint が未設定の場合

- **WHEN** `llm.provider: production_api` で `llm.azure.endpoint` が未設定の config を検証する
- **THEN** `ConfigValidationError` が送出されること

#### Scenario: llm.azure の設定が正常に検証される

- **WHEN** `endpoint`・`deployment`・`production_approved: true` を設定した config を検証する
- **THEN** 検証が成功し `LLMConfig` が構築されること
