## Context

#26 で Admin UI/API と Python core の境界は「read は PostgreSQL 直読み、write は AdminCommand enqueue」に決まった。#28 で `admin_commands` テーブルと UNIQUE `idempotency_key` が実装済みである。#31 はこの境界を使う最初の TypeScript / Node.js skeleton であり、Python core の状態遷移や SharePoint publish を再実装しないことが重要になる。

## Decisions

- `admin-api/` を root に追加し、Node 標準 HTTP API + TypeScript で skeleton を作る。runtime dependency は PostgreSQL 接続用の `pg` のみとする。
- API の中核は pure handler/service と `AdminApiStore` interface に分け、unit test は fake store で外部 DB なしに検証する。
- PostgreSQL adapter は既存 migration の列名に合わせて read / enqueue / command status を実装する。
- state-changing `PATCH` / `POST` は `Idempotency-Key` header を必須にする。保存用 key は `admin-api:<draft_id>:<command_type>:<client-key>` とし、route と command type を含めて意図しない横衝突を避ける。
- 非同期 UX は accepted/pending 応答に `statusUrl` を返し、`GET /api/commands/{command_id}` で status と error details を読む。
- M1 skeleton の auth は `x-spautopost-user` / `x-spautopost-roles` header に限定する。本番 Entra ID/OIDC、Azure Container Apps Authentication、group/app role mapping は #29 で扱う。

## Non-Goals

- 本格 UI design。
- Entra ID / OIDC 実装。
- 複雑な RBAC。
- Python core の state machine 実装。
- Microsoft Graph 呼び出しまたは SharePoint 投稿。
- DB migration 変更。

## Risks / Trade-offs

- Header principal は本番認証ではないため、deployment で外部公開してはならない。README と spec で #29 の対象として残す。
- PostgreSQL adapter は local unit test では fake store で検証する。実 DB contract は #28 storage tests が担保し、Node adapter の実 DB 結合は後続の integration 環境で広げる。
