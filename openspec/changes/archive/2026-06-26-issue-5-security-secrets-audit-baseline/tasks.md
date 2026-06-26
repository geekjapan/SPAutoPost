## 1. docs/specs の更新

- [x] 1.1 `docs/specs/security-baseline.md` の Status を Proposed → Approved に変更する
- [x] 1.2 `docs/specs/audit-log.md` の Status を Proposed → Approved に変更する
- [x] 1.3 `docs/specs/security-baseline.md` に「自動公開を初期対象外とする安全方針」のセクションを追加・明記する（受け入れ条件対応）
- [x] 1.4 `docs/specs/audit-log.md` に監査ログ最小項目（必須 5 フィールド）のセクションを補完する（受け入れ条件対応）

## 2. OpenSpec capability specs の作成

- [x] 2.1 `openspec/specs/security-baseline/spec.md` を作成し、change の specs から内容をアーカイブする（`opsx:archive` 実行）
- [x] 2.2 `openspec/specs/audit-log-baseline/spec.md` を作成し、change の specs から内容をアーカイブする（`opsx:archive` 実行）

## 3. 検証

- [x] 3.1 `openspec validate issue-5-security-secrets-audit-baseline --strict` が通ること
- [x] 3.2 受け入れ条件チェックリスト（#5）を全項目確認し、充足を確認する
- [x] 3.3 `ecc:security-review` によるレビューを実施し、CRITICAL / HIGH がないことを確認する

## 4. PR 作成

- [x] 4.1 変更ファイルをステージし、`docs: define security and audit baseline (Issue #5)` でコミットする
- [x] 4.2 base: main で PR を作成し、受け入れ条件の充足を PR 説明に記載する
