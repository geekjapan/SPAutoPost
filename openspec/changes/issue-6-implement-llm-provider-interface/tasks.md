## 1. OpenSpec

- [x] 1.1 Issue #6 の目的・範囲・非対象範囲を proposal / design / specs / tasks に反映する
- [x] 1.2 `openspec validate issue-6-implement-llm-provider-interface --strict` を通す

## 2. Config

- [x] 2.1 `llm.provider` の許容値を `production_api` / `production_flow` / `generic_api` / `test_mock` / `test_manual` に更新する
- [x] 2.2 provider selection validation の unit test を更新する

## 3. LLM provider interface

- [x] 3.1 `DraftInput` / `DraftOutput` / provider metadata / provider status DTO を追加する
- [x] 3.2 `LLMProvider` Protocol を追加する

## 4. Mock provider

- [x] 4.1 外部通信しない `test_mock` provider を追加する
- [x] 4.2 fixture response と deterministic fallback response を unit test で確認する

## 5. Factory / validation

- [x] 5.1 `LLMConfig` から provider を解決する factory を追加する
- [x] 5.2 未実装 provider type は表現だけ可能とし、構築時は明示的に拒否する

## 6. 検証

- [x] 6.1 `pytest` を通す
- [x] 6.2 `ruff check` と `mypy` を通す
