## 1. OpenSpec change

- [x] 1.1 `azure-hosted-core` capability の delta spec を作成する
- [x] 1.2 `openspec validate issue-24-finalize-azure-hosted-core-architecture --strict` を通す

## 2. Docs 補足（最小差分）

- [x] 2.1 `docs/specs/architecture.md` に未決事項の Issue リンク（storage=#28、identity=#27 / #29 / #32、logging=#30）と Issue #24 受け入れ note を追記する
- [x] 2.2 ADR `2026-06-22-azure-hosted-core.md` が Accepted であることを確認し、必要時のみ Related Issue を補う（既に Accepted・リンク十分のため変更なし）
- [x] 2.3 `docs/specs/deployment.md` の M1 skeleton 範囲が #24 受け入れ条件を満たすことを確認する（既に満たすため変更なし）

## 3. Verification

- [x] 3.1 `openspec validate --changes --strict` を通す
- [x] 3.2 `git diff --check` で whitespace 異常がないことを確認する
- [ ] 3.3 PR を作成する（Closes #24、M0、OpenSpec change ID、verification、security notes）
