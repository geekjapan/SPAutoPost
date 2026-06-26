# Admin UI/API Specification

## Status

Accepted for M1 boundary

## Purpose

この Spec は、M1 で実装する TypeScript / Node.js Admin UI/API の最小機能、画面、API、Python core との境界を定義します。

## Scope

M1 の Admin UI/API は、生成済み DraftPost を管理者が確認、修正、確定し、SharePoint 投稿へ進めるための最小 UI/API です。

## Technology Decision

- Runtime: Node.js
- Language: TypeScript
- Identity: Microsoft Entra ID
- Database: PostgreSQL
- Core processing: Python jobs / CLI commands

## Boundary Summary

M1 の Admin UI/API と Python core の境界は、ADR
`docs/decisions/2026-06-22-admin-core-boundary.md` に従います。

- Read: Admin API は PostgreSQL から DraftPost / ReviewEvent / AuditEvent を直読みする。
- Write: Admin API は DraftPost の状態機械を直接更新しない。
- Command handoff: edit / approve / reject / request regeneration / publish request は
  `AdminCommand` を enqueue し、accepted/pending を返す。
- Processing: Python core/job が pending command を claim し、遷移検証、状態更新、
  ReviewEvent / AuditEvent 記録、publish 処理を所有する。
- UX: M1 は非同期 feedback とする。UI は pending から succeeded / failed を後追い表示する。

## Minimal Screens

### DraftPost List

目的:

- 生成済み記事を一覧する。
- status、urgency、title、updated_at、validation warning を確認する。

### DraftPost Detail

目的:

- 記事本文、出典、影響、対応方法、管理者向け補足を確認する。
- validation warning を確認する。

### DraftPost Edit

目的:

- 管理者が記事を修正する。
- Admin API は edit command を enqueue する。
- Python core が command を処理し、修正履歴を AuditEvent / ReviewEvent に記録する。

### Review / Approval

目的:

- approve
- reject
- request regeneration
- publish request
- これらはすべて `AdminCommand` として受け付け、DraftPost の状態変更は Python core が行う。

### Audit View

目的:

- DraftPost ごとの生成、修正、承認、投稿結果を確認する。

## Minimal API

```text
GET    /api/drafts
GET    /api/drafts/{draft_id}
PATCH  /api/drafts/{draft_id}
POST   /api/drafts/{draft_id}/approve
POST   /api/drafts/{draft_id}/reject
POST   /api/drafts/{draft_id}/regenerate
POST   /api/drafts/{draft_id}/publish-request
GET    /api/commands/{command_id}
GET    /api/drafts/{draft_id}/audit-events
```

API の責務:

- `GET` は PostgreSQL read のみを行い、状態を変更しない。
- `PATCH` / `POST` は request validation と authorization を行い、`AdminCommand`
  を 1 件 enqueue して accepted/pending を返す。
- 状態を変更する `PATCH` / `POST` は client 供給の `Idempotency-Key` を必須とする。
  Admin API は route / draft / command type と組み合わせた保存用 key を作り、
  同一 key の retry では既存 command status を返す。
- `GET /api/commands/{command_id}` は command status / error_code / error_message を返し、
  非同期 reviewer UX の pending -> succeeded / failed 表示に使う。
- publish request は「投稿してよい」という intent であり、Microsoft Graph 呼び出しや
  SharePoint 投稿処理を Admin API 内で実行しない。

## Boundary with Python Core

M1 では、Admin UI/API と Python core は PostgreSQL を共有 state として利用します。

- Python jobs: collect / normalize / generate / validate / publish
- Admin UI/API: list / detail / edit command / approve command / reject command /
  request-regeneration command / publish-request command
- PostgreSQL: shared state

Admin UI/API は、重い生成処理、状態遷移、投稿処理を直接実行しません。必要な操作は
`AdminCommand` として保存し、Python jobs が処理できるようにします。

## M1 Scope

M1 に含めるもの:

- DraftPost list / detail / validation warning display
- edit / approve / reject / request regeneration / publish request の command 受付
- accepted/pending と succeeded/failed を扱う非同期 reviewer UX
- command status read path
- AuditEvent / ReviewEvent 参照
- PostgreSQL 直読みと AdminCommand enqueue の境界
- TypeScript / Node.js の Admin UI/API skeleton

M2 以降に送るもの:

- 本格 UI design
- 複雑な多人数 workflow
- Teams / ITSM integration
- 高度な RBAC と細かな approval policy
- long-running Python HTTP service による同期状態遷移
- Admin API 内での Microsoft Graph publish 実行

## Authentication and Authorization

- Admin login は Microsoft Entra ID を使う。
- M1 の role は viewer / reviewer / approver / publisher / admin とする。
- role mapping は Entra ID group または app role を候補とする。
- 管理者操作は AuditEvent に記録する。

## Non-Goals

- 本格 UI design
- 複雑な多段承認
- Teams 通知
- ITSM 連携
- 複雑な RBAC

## Related Issues

- #26 Define TypeScript Node.js Admin UI/API boundary
- #28 Implement PostgreSQL storage baseline
- #29 Implement Entra ID login for Admin API/UI
- #31 Implement TypeScript Node.js Admin UI API skeleton
