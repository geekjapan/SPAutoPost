## 1. OpenSpec change

- [x] 1.1 `design-document-review` capability の proposal / design / spec / tasks を作成する
- [x] 1.2 `openspec validate issue-23-review-finalize-detailed-design-documents --strict` を docs 編集前に通す

## 2. Docs（最小差分・中央マトリクス集約）

- [x] 2.1 `docs/design-documents.md` に Review & Status Matrix (Issue #23) を追加し、18 対象文書を M0 disposition で分類する中央レビュー記録とする
- [x] 2.2 `docs/specs/data-model.md` の Status を Proposed → Accepted for M0 に更新する（#3 で canonical model merge 済み）
- [x] 2.3 `docs/specs/configuration.md` の Status を Proposed → Accepted for M0 に更新する（#4 で configuration capability archive 済み）
- [x] 2.4 SharePoint 残未決事項の #2 集約、LLM provider 未決事項の #15 集約を中央マトリクスで明示する
- [x] 2.5 M0 spec 不足（#2 / #5 / #27）と後続 spec の既存 Issue 追跡を中央マトリクスに記録する（新規 Issue は作成しない）
- [x] 2.6 review feedback に基づき、Graph auth matrix 行、Accepted for M0 定義、spec index status、SharePoint MVP mode の settled decision を同期する

## 3. Verification

- [x] 3.1 `openspec validate issue-23-review-finalize-detailed-design-documents --strict` を通す
- [x] 3.2 `openspec validate --all --strict` を通す
- [x] 3.3 `git diff --check` で whitespace 異常がないことを確認する
- [x] 3.4 PR を作成する（Closes #23、M0、OpenSpec change ID、verification、spec delta、security notes、follow-up issues）
