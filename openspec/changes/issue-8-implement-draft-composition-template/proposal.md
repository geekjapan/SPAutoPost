## Why

Issue #8 は、手動または正規化済みの Advisory から SharePoint お知らせ掲示板向けの DraftPost を作るための文面テンプレートを必要としている。既存の LLM provider interface と mock provider はあるが、M1 の draft 品質要件である利用者向け・管理者向け欄、出典保持、guardrail、prompt version 記録がまだ実装されていない。

## What Changes

- Advisory / DraftInput から SharePoint announcements 向け DraftOutput を組み立てる composition template を追加する。
- title、summary for users、impact、required actions、admin actions、deadline / urgency、references を埋める。
- 出典にない断定と攻撃手順の詳細化を避ける guardrail を template / warning として保持する。
- 生成結果に prompt version と deterministic input hash を記録する。
- 本番 LLM provider 接続、HTML/web-part 最終 layout、多言語対応は追加しない。

## Capabilities

### New Capabilities

- `draft-composition-template`: Advisory から SharePoint announcement 用 DraftPost 相当の DraftOutput を生成する template と guardrail を扱う。

### Modified Capabilities

- なし。

## Impact

- `src/spautopost/llm/`
- `tests/llm/`
- `openspec/changes/issue-8-implement-draft-composition-template/`
