## Why

SPAutoPost は複数の生成 AI provider（Microsoft Foundry / Azure OpenAI、Copilot Studio、OpenAI-compatible API、手動 ChatGPT / Claude 取込）を想定しているが、実稼働 provider とテスト provider の分類・利用条件・入力データ制限・監査項目が Spec として明文化されていない。M3 での production provider 実装（Issue #16 / #17）が本 Spec を契約（contract）として参照するため、今 Spec を確定する必要がある。

## What Changes

- `docs/specs/llm-provider.md` に以下の項目を追加・強化する:
  - provider 分類（production_api / production_flow / generic_api / test_mock / test_manual）の要件を SHALL / MUST 形式で明文化
  - ChatGPT / Claude subscription を自動化前提にしない方針の明示（test_manual 扱い・禁止事項）
  - provider へ渡してよい情報 / 禁止情報の定義（`security-baseline.md` のデータ最小化方針との整合）
  - prompt / output 保存方針の明文化
  - provider 切替方針の明文化
  - provider ごとの監査項目の定義（SHALL / MUST ベースのシナリオ付き）
- `docs/specs/security-baseline.md` の LLM 入力制限セクションとの整合確認（差分が生じた場合は security-baseline を更新）

## Capabilities

### New Capabilities

なし（既存 `llm-provider` spec の強化）

### Modified Capabilities

- `llm-provider`: provider 分類要件・入力制限・監査項目・テスト/実稼働分離方針の SHALL / MUST 化と Scenario 追加

## Impact

- 影響ドキュメント: `docs/specs/llm-provider.md`、必要に応じて `docs/specs/security-baseline.md`
- 影響コード: なし（Spec のみ）
- 影響 Issue: #16（Azure OpenAI provider 実装）、#17（generic API provider 実装）、#18（AI output validation）が本 Spec を前提条件として参照する
- 外部 API・Secret・投稿処理への変更はない
