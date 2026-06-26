## Why

M1 MVP では mock/template による DraftPost 生成を必須とするが、記事生成の実用感を確認するために optional LLM provider（Azure OpenAI / Foundry、generic API）を試す必要がある。現状の `docs/specs/llm-provider.md` は provider 分類と interface を定義しているが、M1 に含めるか・M3 以降に先送りするかの判断材料（API 利用条件・認証方式・コスト・リスク）が未整理のため、この Spike で評価し投入判断を確定する。

## What Changes

- `docs/specs/llm-provider.md` に Spike 評価結果（M1/M3 判断、provider 候補ごとの実装可能性）を追記する
- `docs/decisions/2026-06-22-llm-provider-strategy.md` を Spike 結果に基づき更新し、M1 スコープを明確化する
- provider interface 要件（`DraftInput` / `DraftOutput` / error handling）の確定版を spec に反映する
- test_manual provider の M1 における扱い（手動取込フロー）を明文化する
- Foundry / Azure OpenAI provider を M1 に含めない場合は、M3 実装 Issue (#16) の前提条件を更新する

## Capabilities

### New Capabilities

- `llm-provider-evaluation`: LLM provider 候補（Azure OpenAI, Foundry, generic API, test_manual）の M1/M3 採用判断根拠、interface 要件確定、Spike 結果を docs に記録する capability

### Modified Capabilities

- `llm-provider`: 既存の `docs/specs/llm-provider.md` に Spike 評価結果・M1 スコープ決定・provider interface 確定版を追加反映する

## Impact

- `docs/specs/llm-provider.md` — 更新（評価結果・interface 確定）
- `docs/decisions/2026-06-22-llm-provider-strategy.md` — 更新（M1 スコープ判断）
- Issue #16 (Azure OpenAI provider), #17 (generic API provider) — M1/M3 判断が依存先
- Issue #6 (mock provider interface) — interface 確定後に整合を確認
- 実装コード: M1 時点では src/ に LLM 呼び出しコードは追加しない（Spike = docs 評価のみ）
