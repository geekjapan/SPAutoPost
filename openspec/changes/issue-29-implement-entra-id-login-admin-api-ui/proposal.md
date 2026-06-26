## Why

Issue #29（M1）は、Admin API/UI のログイン認証を Microsoft Entra ID 連携に置き換えることを必要としている。#31 の Admin API skeleton は、開発用の偽装可能な header（`x-spautopost-user` / `x-spautopost-roles`）で principal を受けており、その spec（`admin-ui-api-skeleton` の Development auth boundary）は「本番 Entra ID login と role mapping は #29 で扱う」と明示している。

`docs/decisions/2026-06-22-admin-authentication-entra-id.md` と `docs/specs/admin-authentication.md` は、Admin API/UI のログインを Microsoft Entra ID に統一し、reviewer / approver / publisher / admin / viewer の最小 role を Entra group または app role で表現し、管理者操作を user principal として AuditEvent に記録する方針を確定済み。spec の Preliminary Recommendation は Azure Container Apps Authentication（EasyAuth）+ Entra ID を第一候補とする。

## What Changes

- Admin API の認証を、開発用 header trust から **Entra ID 認証済み principal の必須化**へ移行する。未認証要求は read / write とも拒否する（401）。
- 認証済み principal（principal id / principal name / display name / roles）を Entra ID claim から導出する。
- Entra の app role / group claim を reviewer / approver / publisher / admin / viewer に mapping する。未知の値は role として採用しない。
- 管理者操作の AuditEvent context に user principal（id / name / display / roles）を伝播し、token / cookie / authorization header 等の secret は記録しない。
- local dev 用の認証代替（dev header principal）は明示的な opt-in 設定でのみ有効化し、本番設定では fail closed にする（既定は本番安全側 = Entra 認証必須）。
- Admin login 認証と Microsoft Graph service 認証を分離したまま維持する（本 change は Graph 認証に触れない）。

## Capabilities

### New Capabilities

- `admin-authentication`: Admin API/UI の Entra ID login 前提、認証済み principal の必須化、role mapping、user principal の audit 伝播、dev 認証代替の本番無効化、Admin login と Graph service 認証の分離。

## Impact

- **コード**: `admin-api/src/`（auth module 追加、handler/service の principal 解決変更）
- **テスト**: `admin-api/test/`（auth unit test、既存 skeleton test の dev-mode 明示化）
- **Docs/specs**: `docs/specs/admin-authentication.md`（Status 更新）、`openspec/specs/admin-authentication/`（archive 時 sync）
- **Security**: 認証 / 認可 に触れる carve-out。実 token / Secret / client secret は扱わず、in-app token 保管も行わない。merge は人間承認を要する（auto-merge しない）。
- **非対象**: 複雑な多段 RBAC、外部ユーザー認証、Graph service 認証の最終決定、本番 tenant の app registration 作成。
