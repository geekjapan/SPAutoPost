## 1. OpenSpec artifacts

- [x] 1.1 Issue #3 / M0 / 受け入れ条件に沿った proposal / design / spec / tasks を作成する
- [x] 1.2 `data-model` capability に主要エンティティ・必須項目・トレーサビリティ・idempotency・provenance・collector 分離 input model・Secret 非保存の requirement を定義する

## 2. Docs reconcile

- [x] 2.1 `docs/specs/initial-system.md` の「Core Data Models」に `data-model.md` を正本とする cross-reference と AuditEvent の所在を追記する（実体は重複させない）
- [x] 2.2 `docs/specs/data-model.md` を normative reference として参照し、フィールド表を二重管理しない

## 3. Verification

- [x] 3.1 `openspec validate issue-3-define-core-data-model --strict` を実行する
- [x] 3.2 `openspec validate --changes --strict` を実行する
- [x] 3.3 `git diff --check` を実行する（コード・migration 変更なしを確認）
