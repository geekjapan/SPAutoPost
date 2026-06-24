## Why

Issue #31 は、M1 で管理者が DraftPost を確認し、修正・承認・差し戻し・再生成・投稿要求へ進める TypeScript / Node.js Admin UI/API skeleton を必要としている。#26 / #28 で Admin API と Python core の境界、および AdminCommand 永続化が確定したため、Node 側は read を PostgreSQL 直読み、write を AdminCommand enqueue に限定した最小 API を実装できる。

PR #48 の post-merge review で、state-changing write の idempotency 契約と非同期 command status read path が #31 実装に必要であることも判明した。本 change は skeleton 実装と同時に、それらの境界 spec を修正する。

## What Changes

- TypeScript / Node.js の Admin API skeleton を追加する。
- DraftPost list / detail / audit read endpoint と、AdminCommand status read endpoint を追加する。
- edit / approve / reject / request-regeneration / publish-request の入口を追加し、実処理は AdminCommand enqueue に限定する。
- state-changing write は client 供給の `Idempotency-Key` を必須にする。
- PostgreSQL 用 store adapter を追加し、既存 SQL schema の `draft_posts` / `review_events` / `audit_events` / `admin_commands` に合わせる。
- 開発用の仮 principal header と role header を使う。Entra ID/OIDC 本実装、複雑な RBAC、実 SharePoint publish は追加しない。
- CI に Node Admin API check を追加する。

## Capabilities

### New Capabilities

- `admin-ui-api-skeleton`: TypeScript / Node.js Admin API skeleton、read path、AdminCommand enqueue、command status read path。

### Modified Capabilities

- `admin-api-boundary`: state-changing request の idempotency 契約を client `Idempotency-Key` 必須へ修正し、command status read path を明記する。

## Impact

- **新規コード**: `admin-api/`
- **Node tooling**: `package.json`, `package-lock.json`
- **CI**: Node Admin API checks
- **Docs/specs**: `docs/specs/admin-ui-api.md`, `docs/specs/architecture.md`, `docs/design-documents.md`, `openspec/specs/admin-api-boundary/spec.md`
- **Security**: 実 token / Secret / Entra ID / Microsoft Graph / SharePoint 投稿は扱わない。Admin API skeleton は local/dev 用 header principal を受けるが、本番認証は #29 の対象。
