## Why

Issue #17 の目標：設定だけで任意の OpenAI-compatible LLM API を有効化できる `generic_api` provider adapter を実装する。現状の `build_llm_provider` は `test_mock` のみに対応しており、実稼働 API 呼び出しのパスが存在しない。M3 前提条件（利用条件・vendor 選定・監査ログ方法の確認）は Issue #15 で記録済みとして本 change では adapter 実装に集中する。

## What Changes

- `src/spautopost/llm/generic_provider.py` を新規追加：`GenericApiLLMProvider` クラス（`LLMProvider` protocol を実装）
- `src/spautopost/config.py`：`LLMConfig` に `generic_api` 向けフィールド（`endpoint_url`, `model`, `auth_env_var`, `timeout_seconds`, `max_retries`）を追加。`_SECTION_KEYS["llm"]` を拡張
- `src/spautopost/llm/__init__.py`：`build_llm_provider` が `generic_api` を `GenericApiLLMProvider` に routing
- `tests/llm/test_generic_provider.py` を新規追加：TDD で mock HTTP を使ったテスト
- `tests/llm/test_provider.py`：`generic_api` の `LLMProviderConfigError` テストを削除し、正常 build テストに更新

## Capabilities

### New Capabilities

- `generic-llm-provider`: OpenAI-compatible REST API を設定駆動で呼び出す `generic_api` provider adapter。endpoint / model / auth / request template / response mapping / timeout・retry / provider metadata の各項目を設定または実装で分離する。監査ログ必須項目（provider_name, provider_type, model, prompt_version, generation_input_hash, generated_at）を `ProviderMetadata` に含める。Secret（auth header 値）はコード・ログに出力しない。

### Modified Capabilities

- `llm-provider`: `build_llm_provider` が `generic_api` を受け付けるよう interface を拡張。`LLMConfig` に generic_api 設定フィールドを追加（既存の `test_mock` パスに影響なし）。

## Impact

- `src/spautopost/config.py`：`LLMConfig` 拡張、`_SECTION_KEYS["llm"]` 拡張（後方互換）
- `src/spautopost/llm/__init__.py`：`build_llm_provider` 拡張（後方互換）
- 新規ファイル：`src/spautopost/llm/generic_provider.py`、`tests/llm/test_generic_provider.py`
- 依存：HTTP 通信に stdlib `urllib.request` を使用（新規 dependency なし）
- セキュリティ：auth header 値を env から取得、ログ・例外に含めない（`secrets.py` パターンを踏襲）
- 非公式 UI 自動操作・scraping は本 adapter の対象外（`test_manual` 扱い）
