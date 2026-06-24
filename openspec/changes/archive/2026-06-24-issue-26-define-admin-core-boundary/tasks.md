## 1. 境界 spec の確定

- [x] 1.1 `admin-api-boundary` capability spec の requirement/scenario を確定（read 直読み / write 非同期 command / Python 遷移所有 / 非同期 UX）
- [x] 1.2 `docs/specs/admin-ui-api.md` を本境界に整合させて更新
- [x] 1.3 `architecture.md` の該当 Open Question が解消済みであることを参照で明示

## 2. 契約の整合確認

- [x] 2.1 #28 storage capability の AdminCommand 契約（columns / idempotency_key / claim 操作）と本境界 spec が矛盾しないことを確認
- [x] 2.2 状態遷移セット（approve / reject / request-regeneration / edit / publish-request）と DraftStatus の対応を確認
- [x] 2.3 spec scenario を #31 / #28 のテスト観点として流用できる形に整える

## 3. 検証

- [x] 3.1 openspec validate が通ることを確認
- [x] 3.2 受け入れ条件（Issue #26）の充足を確認
