## 1. テスト先行（TDD）

- [ ] 1.1 `tests/llm/test_azure_openai.py` を新規作成し、`AzureOpenAIProvider` の全シナリオのテストを書く（RED）
- [ ] 1.2 `tests/test_config.py` に `llm.azure` サブセクションの検証テストを追加する（RED）

## 2. 設定スキーマ拡張

- [ ] 2.1 `config.py` の `LLMConfig` に `azure` サブセクション用フィールドを追加する
- [ ] 2.2 `config.py` の `_SECTION_KEYS["llm"]` に `azure` を追加し、`_validate_llm` で azure サブセクションを検証する（endpoint / deployment 必須チェック、production_approved チェック）
- [ ] 2.3 `config.example.yml` に `production_api` provider の設定例を追加する

## 3. AzureOpenAIProvider 実装

- [ ] 3.1 `src/spautopost/llm/azure_openai.py` を新規作成し、`AzureOpenAIConfig` dataclass を定義する
- [ ] 3.2 `AzureOpenAIProvider.__init__` を実装する（config バリデーション、metadata 構築）
- [ ] 3.3 `validate_config` を実装する（production_approved フラグ、endpoint / deployment 存在確認）
- [ ] 3.4 `get_provider_metadata` を実装する
- [ ] 3.5 `_build_request_body` を実装する（DraftInput → Chat Completions リクエスト JSON 変換、system prompt 構築）
- [ ] 3.6 `_call_api` を実装する（urllib.request で HTTP POST、api-key ヘッダ設定）
- [ ] 3.7 `_parse_response` を実装する（レスポンス JSON → DraftOutput 変換、必須フィールド検証）
- [ ] 3.8 `_retry_loop` を実装する（指数バックオフ、retryable / non-retryable 分岐）
- [ ] 3.9 `generate_draft` を実装する（retry_loop 呼び出し、監査 metadata 付与）
- [ ] 3.10 `LLMProviderError` を `src/spautopost/llm/__init__.py` に追加する（`is_retryable: bool` フィールド付き）

## 4. build_llm_provider 拡張

- [ ] 4.1 `build_llm_provider` に `production_api` ブランチを追加し、`AzureOpenAIProvider` を返す
- [ ] 4.2 `src/spautopost/llm/__init__.py` の `__all__` に `AzureOpenAIProvider` と `LLMProviderError` を追加する

## 5. テスト GREEN → 品質確認

- [ ] 5.1 すべてのテストが PASS することを確認する（`pytest tests/llm/`）
- [ ] 5.2 型検査が通ることを確認する（`mypy src`）
- [ ] 5.3 lint が通ることを確認する（`ruff check . && ruff format --check src tests`）
- [ ] 5.4 カバレッジ 80% 以上を確認する（`pytest --cov=spautopost --cov-report=term-missing`）
