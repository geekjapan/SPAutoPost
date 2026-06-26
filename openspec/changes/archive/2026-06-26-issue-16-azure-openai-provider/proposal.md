## Why

M1 では `test_mock` provider のみで DraftPost 生成を実現してきたが、M3 では実 LLM API を使った本番品質の原稿生成が必要になる。Microsoft Foundry / Azure OpenAI は組織が管理する enterprise 向け API であり、Entra ID 認証・データ残留制御・監査ログの観点から最優先の `production_api` 候補として Issue #15 で確定済みである。

## What Changes

- `AzureOpenAIProvider` クラスを `src/spautopost/llm/azure_openai.py` として新規実装する
- `LLMProvider` interface（`validate_config` / `generate_draft` / `get_provider_metadata`）を実装する
- `DraftInput → DraftOutput` 変換を Azure OpenAI Chat Completions API（`/openai/deployments/{deployment}/chat/completions`）で実現する
- HTTP は stdlib `urllib.request` を使用し、新規ランタイム依存を追加しない
- timeout・retry（指数バックオフ）・エラーマッピング（`LLMProviderError`）を実装する
- 監査 metadata（`provider_name` / `model` / `prompt_version` / `token_usage` / `generation_input_hash`）を `DraftOutput` に付与する
- API key は `env:AZURE_OPENAI_API_KEY` 形式で config から参照し、コード・ログ・fixture に直書きしない
- `build_llm_provider` が `production_api` を選択した場合に `AzureOpenAIProvider` を返すよう更新する
- `config.py` の `llm` セクションに `azure` サブセクション（`endpoint` / `deployment` / `api_version` / `auth_type` / `timeout_secs` / `max_retries` / `production_approved`）を追加する
- 環境 / provider_type 組み合わせ検証（production 環境では test_mock 禁止）を `validate_config` に追加する

## Capabilities

### New Capabilities

- `azure-openai-provider`: Azure OpenAI / Foundry provider adapter。設定・認証・HTTP・retry・構造化出力・監査 metadata を含む

### Modified Capabilities

- `llm-provider`: `build_llm_provider` が `production_api` を受け入れる拡張と、`production_approved` フラグによる起動時ブロックを追加する

## Impact

- **実装ファイル**: `src/spautopost/llm/azure_openai.py`（新規）、`src/spautopost/llm/__init__.py`（拡張）、`src/spautopost/config.py`（llm.azure サブセクション追加）
- **テストファイル**: `tests/llm/test_azure_openai.py`（新規）、`tests/test_config.py`（llm.azure 設定検証追加）
- **config example**: `config.example.yml` に azure provider 設定例を追加
- **新規依存なし**: stdlib urllib 使用。managed identity 対応は optional extra（将来）
- **後方互換**: 既存の `test_mock` ブランチは変更なし。`production_api` が未設定の場合は従来どおりエラー
