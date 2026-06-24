## 1. OpenSpec artifacts

- [x] 1.1 Issue #31 / M1 / #26 boundary / #28 storage に沿った proposal / design / spec / tasks を作成する
- [x] 1.2 PR #48 review follow-up（client Idempotency-Key 必須、command status read path、Status Policy、責務表現）を spec/docs に反映する

## 2. TypeScript / Node skeleton

- [x] 2.1 `admin-api/` に TypeScript project skeleton と root npm scripts を追加する
- [x] 2.2 DraftPost list/detail/audit read handler を追加する
- [x] 2.3 edit / approve / reject / request-regeneration / publish-request を AdminCommand enqueue として実装する
- [x] 2.4 `Idempotency-Key` 必須 validation と retry dedupe response を実装する
- [x] 2.5 command status read path を実装する
- [x] 2.6 PostgreSQL schema に合わせた store adapter を追加する

## 3. Tests and CI

- [x] 3.1 Admin API handler/service の unit test を追加する
- [x] 3.2 CI に Node Admin API checks を追加する

## 4. Docs

- [x] 4.1 README に Admin API skeleton の起動・検証方法を追記する
- [x] 4.2 OpenSpec / project checks を実行し、結果を PR に記録する
