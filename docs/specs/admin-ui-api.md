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

M1 の Admin UI/API と Python core の呼び出し境界は ADR `admin-core-boundary.md` で決定済み。
capability spec `admin-api-boundary`（openspec/changes/issue-26-define-admin-core-boundary/specs/admin-api-boundary/spec.md）が契約の正本。

### Read — 直読み

Admin API（TypeScript/Node）は DraftPost / ReviewEvent / AuditEvent の一覧・詳細・audit 参照を
PostgreSQL から直接 read してよい。read 経路はドメイン状態を変更してはならない。

### Write — AdminCommand 経由の非同期 handoff

approve / reject / request-regeneration / edit / publish-request の状態遷移 Write は、
Admin API が auth/RBAC とリクエスト形式 validation のみ実施し、idempotent な AdminCommand を
1 件挿入して `accepted/pending` を返す。Admin API がドメイン状態機械を直接更新してはならない。

### 責務分担

| 層 | 責務 |
|---|---|
| Admin API (TS) | auth/RBAC、リクエスト形式 validation、idempotency_key 発番、AdminCommand enqueue |
| Python core/job | pending command 消費、遷移妥当性検証、状態遷移、ReviewEvent 記録、AuditEvent 記録 |

### 非同期 UX

M1 のフィードバックは非同期（accepted/pending → succeeded/failed の後追い表示）。
同期成功/失敗フィードバックと long-running Python HTTP サービスは M1 対象外。

### idempotency_key

Admin API server 側で発番する。client が request-id を供給した場合のみ併用して重複検知を強める。

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
