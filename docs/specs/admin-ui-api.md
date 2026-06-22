# Admin UI/API Specification

## Status

Proposed

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
- 修正履歴を AuditEvent / ReviewEvent に記録する。

### Review / Approval

目的:

- approve
- reject
- request regeneration
- publish request

### Audit View

目的:

- DraftPost ごとの生成、修正、承認、投稿結果を確認する。

## Minimal API

候補:

```text
GET    /api/drafts
GET    /api/drafts/{draft_id}
PATCH  /api/drafts/{draft_id}
POST   /api/drafts/{draft_id}/approve
POST   /api/drafts/{draft_id}/reject
POST   /api/drafts/{draft_id}/regenerate
POST   /api/drafts/{draft_id}/publish-request
GET    /api/drafts/{draft_id}/audit-events
```

## Boundary with Python Core

M1 では、Admin UI/API と Python core は PostgreSQL を共有 state として利用します。

- Python jobs: collect / normalize / generate / validate / publish
- Admin UI/API: list / detail / edit / approve / publish request
- PostgreSQL: shared state

Admin UI/API は、原則として重い生成処理や投稿処理を直接実行しません。必要な操作は state を変更し、Python jobs が処理できるようにします。

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
- #29 Implement Entra ID login for Admin API/UI
- #31 Implement TypeScript Node.js Admin UI API skeleton
