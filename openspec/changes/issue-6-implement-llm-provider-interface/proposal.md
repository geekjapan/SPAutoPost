## Why

掲示板原稿生成は実稼働 LLM とテスト用 provider を分離する必要がある。M1 では外部 LLM 接続を実装せず、後続 issue が依存できる provider interface と deterministic mock を先に固定する。

## What Changes

- `DraftInput` / `DraftOutput` と LLM provider の最小 interface を追加する。
- `test_mock` provider を追加し、fixture から deterministic な draft を返せるようにする。
- provider type として `production_api` / `production_flow` / `generic_api` / `test_mock` / `test_manual` を config で選択できるようにする。
- provider config validation を追加する。
- production provider の実接続、UI 自動操作、Issue #7 の下書き生成テンプレート実装は含めない。

## Capabilities

### New Capabilities

- `llm-provider-interface`: LLM provider interface、Draft DTO、mock provider、provider config validation。

### Modified Capabilities

- `configuration`: `llm.provider` の許容値を Issue #6 の provider type に合わせる。

## Impact

- 影響コード: `src/spautopost/config.py`, `src/spautopost/llm/`
- 影響テスト: `tests/test_config.py`, `tests/llm/`
- 外部 API 呼び出し、Secret 追加、投稿処理の変更はない。
