## Context

#31 の Admin API skeleton は、開発用 header（`x-spautopost-user` / `x-spautopost-roles` / `x-spautopost-display-name`）から principal を解決している（`admin-api/src/service.ts: parsePrincipal`）。これは偽装可能で、本番の認証境界にはならない。#29 はこれを Entra ID 認証へ置き換える。

承認された方針（coordinator gate）: **Option A = Azure Container Apps Authentication（EasyAuth）+ app roles**。

## Goals / Non-Goals

Goals:
- Entra ID 認証済み principal を必須化し、未認証を 401 で拒否する。
- EasyAuth が注入する principal header から id / name / display / roles を導出する。
- app-role claim を viewer/reviewer/approver/publisher/admin に 1:1 マップする。
- user principal を AdminCommand 経由で audit へ伝播する。
- dev 認証代替を本番安全側 default + fail-closed にする。

Non-Goals:
- in-app MSAL OIDC（login/callback/PKCE/JWKS/session/client secret）の実装（Option B、spec の fallback）。
- 複雑な多段 RBAC、group-GUID mapping、外部ユーザー認証。
- Microsoft Graph service 認証（別レイヤ、本 change では触れない）。

## Decision: Option A（EasyAuth header trust）

Azure Container Apps Authentication が Entra ID の OIDC/MSAL フローをプラットフォーム側で実行し、認証済み要求に次の header を注入する:

- `X-MS-CLIENT-PRINCIPAL`: base64 エンコードされた JSON（`{ auth_typ, name_typ, role_typ, claims: [{ typ, val }] }`）。
- `X-MS-CLIENT-PRINCIPAL-ID`: principal id（fallback）。
- `X-MS-CLIENT-PRINCIPAL-NAME`: principal name（fallback）。

アプリは token を保持・検証せず、プラットフォームが認証済みと示した principal header を信頼する。これにより in-app secret / token handling / 新規依存が不要になり、spec の Preliminary Recommendation と一致する。既存 skeleton の「注入 header を信頼する」モデルの最小進化でもある。

### Principal 解決（`admin-api/src/auth.ts`）

`X-MS-CLIENT-PRINCIPAL` を base64 デコード → JSON parse し:
- `principalId`: claim `http://schemas.microsoft.com/identity/claims/objectidentifier`（oid）優先、無ければ `X-MS-CLIENT-PRINCIPAL-ID` header。導出不能なら 401。
- `principalName`: `name_typ` に一致する claim（通常 `preferred_username` / upn）、無ければ `X-MS-CLIENT-PRINCIPAL-NAME` header。
- `displayName`: claim `name`（任意）。
- `roles`: `role_typ`（既定 `roles`）に一致する claim 値の集合 = Entra app role values。

### Role mapping（app roles 1:1）

Entra app registration の app role value を、そのまま Admin role 名（`viewer` / `reviewer` / `approver` / `publisher` / `admin`）として発行する想定で 1:1 採用する。既存の `isAdminRole` 判定を再利用し、未知の値は捨てる。有効 role が 0 件の保護対象要求は 403。

ponytail: 直接一致で開始。Entra 側の role 名が将来分岐したら `ADMIN_ROLE_MAP`（JSON env: Entra value -> Admin role）で対応する。group-GUID mapping は不採用（不透明・運用負荷大）。

### Auth mode と fail-closed（`ADMIN_AUTH_MODE`）

`resolveAuthenticator(env)` が mode を決める:
- 既定（未設定）= `easyauth`（本番安全側）。EasyAuth principal を要求。
- `ADMIN_AUTH_MODE=easyauth`: EasyAuth principal を要求。
- `ADMIN_AUTH_MODE=dev`: 既存 dev header parser を使う。**ただし `NODE_ENV=production` なら起動を throw（fail closed）**。
- 未知の値: throw。

default を easyauth にすることで、設定漏れ時も dev bypass が本番で有効化されない（安全側に倒れる）。起動時（`server.ts`）と各 request 解決時の双方で評価する。

### 結線（最小 diff）

- `http.ts: handleAdminApiRequest(store, request, authenticate = resolveAuthenticator())` の任意 3rd 引数で authenticator を注入可能にする。`contextFrom` がそれを使う。
- `createNodeHandler` / `startAdminApiServer` は起動時に `resolveAuthenticator()` を一度評価して fail-closed を早期に検出し、handler へ渡す。
- `service.ts: parsePrincipal` は dev header parser として残す（dev mode で再利用）。

### Audit 伝播

`enqueueDraftCommand` は既に `requestedBy: principal.principalId` を AdminCommand に載せている。Python core がそれを AuditEvent の actor として記録する（boundary spec の所有どおり）。本 change は principal id の伝播経路が EasyAuth 由来の実 principal になることを保証する。token / cookie / authorization は payload secret-key 拒否（既存 `rejectSecretPayload`）と「audit へ出さない」要件で守る。

## Risks / Trade-offs

- EasyAuth header の信頼は、Admin API が EasyAuth 配下（Container Apps）でのみ公開され、直接到達経路が無いことに依存する。デプロイ（#25）で ingress を EasyAuth 経由に限定する前提を doc 化する。ponytail: header spoofing 対策は network 境界に委ねる（アプリ層で署名検証はしない＝Option A の定義どおり）。
- app-role の発行は Entra app registration 側の設定に依存（本 change の非対象 = 手順は M1 follow-up）。

## Migration

- 既存 skeleton test は dev header 前提のため、dev authenticator を明示注入して維持する（API 挙動の test であり auth mechanism の test ではない）。
- 新規 `auth.test.ts` で EasyAuth parse / 401 / role mapping / 403 / fail-closed を検証する。

## Open Questions（M1 follow-up）

- Entra app role value を Admin role 名と一致させるか、`ADMIN_ROLE_MAP` を使うか（運用設定時に確定）。
- Container Apps ingress を EasyAuth 経由のみへ限定する具体設定（#25 デプロイ側）。
