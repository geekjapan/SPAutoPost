## 1. OpenSpec artifacts

- [x] 1.1 Issue #29 / M1 / admin-authentication spec / entra-id decision に沿った proposal / design / spec / tasks を作成する
- [x] 1.2 `openspec validate issue-29-implement-entra-id-login-admin-api-ui --strict` を通す
- [x] 1.3 self-grill（pre-apply gate）で曖昧さを潰す

## 2. Entra ID auth 実装（TDD）

- [x] 2.1 EasyAuth principal parser（`X-MS-CLIENT-PRINCIPAL` base64/JSON → id/name/display/roles）の test を書く（RED）
- [x] 2.2 app-role claim → viewer/reviewer/approver/publisher/admin の 1:1 mapping を実装する（GREEN）
- [x] 2.3 `resolveAuthenticator` の mode 解決と `NODE_ENV=production` 時 dev fail-closed の test を書く（RED）
- [x] 2.4 auth mode 解決（default=easyauth、dev は明示 opt-in + fail-closed）を実装する（GREEN）
- [x] 2.5 `handleAdminApiRequest` / `createNodeHandler` / `startAdminApiServer` に authenticator を結線する
- [x] 2.6 未認証 read / write を 401、role 無しを 403 にする経路を検証する

## 3. Tests / 既存 test 整合

- [x] 3.1 新規 `admin-api/test/auth.test.ts`（EasyAuth parse / 401 / role mapping / 403 / fail-closed）を追加する
- [x] 3.2 既存 skeleton test を dev 明示化（ADMIN_AUTH_MODE=dev）で維持する
- [x] 3.3 `npm run admin-api:check`（typecheck + build + node --test）を green にする（24 tests pass）

## 4. Review / Docs / PR

- [x] 4.1 ecc:code-review を実施し HIGH/CRITICAL を解消する
- [x] 4.2 ecc:security-review（認証 carve-out）を実施し指摘を解消する
- [x] 4.3 `docs/specs/admin-authentication.md` の Status と実装メモを更新する
- [ ] 4.4 PR を作成する（auth carve-out によりマージは人間承認まで保留）
