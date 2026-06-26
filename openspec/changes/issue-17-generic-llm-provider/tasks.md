## 1. Config 拡張

- [ ] 1.1 `LLMConfig` に `endpoint_url`, `model`, `auth_env_var`, `timeout_seconds`, `max_retries` フィールドを追加
- [ ] 1.2 `_SECTION_KEYS["llm"]` に新フィールドを追加
- [ ] 1.3 `_validate_llm` で新フィールドをパース（optional、デフォルト値あり）

## 2. GenericApiLLMProvider 実装（TDD）

- [ ] 2.1 `tests/llm/test_generic_provider.py` 作成：`validate_config` 正常・異常系テスト（RED）
- [ ] 2.2 `tests/llm/test_generic_provider.py`：`generate_draft` mock HTTP テスト（RED）
- [ ] 2.3 `tests/llm/test_generic_provider.py`：タイムアウト・リトライ・error path テスト（RED）
- [ ] 2.4 `src/spautopost/llm/generic_provider.py` 作成：`GenericApiLLMProvider` 実装（GREEN）
- [ ] 2.5 `build_llm_provider` が `generic_api` を `GenericApiLLMProvider` に routing

## 3. 既存テスト更新

- [ ] 3.1 `tests/llm/test_provider.py` の `test_build_llm_provider_rejects_unimplemented_provider_types` から `generic_api` を除外
- [ ] 3.2 `test_build_llm_provider_selects_generic_api` を追加

## 4. 品質確認

- [ ] 4.1 `ruff check . && ruff format --check src tests` をパス
- [ ] 4.2 `mypy src` をパス
- [ ] 4.3 `pytest --cov=spautopost --cov-report=term-missing` でカバレッジ 80% 以上
- [ ] 4.4 Secret が例外メッセージ・ログに含まれないことを確認
