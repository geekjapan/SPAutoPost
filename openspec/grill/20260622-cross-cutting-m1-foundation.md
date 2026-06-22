# Cross-cutting grill — M1 foundation (#28 storage, #26 admin-api-boundary)

Date: 20260622
Changes: issue-28-implement-postgresql-storage-baseline, issue-26-define-admin-core-boundary

## Resolved inline (no user input)
- command_type 値集合を #28 design に列挙（edit|approve|reject|request_regeneration|publish_request）— #26 write set と一致。**Status**: Resolved
- AdminCommand / Intent 用語を AdminCommand に統一。**Status**: Resolved
- SQLite JSON1 前提 / migration runner 選定 / Python 最小 init 所有 → 低リスク、design に明記し apply 時検証。**Status**: Resolved
- 依存 DAG（#28 → #26）・apply 直列（#28 schema 単一ワーカー）・DraftStatus(authoritative)↔AdminCommand(inbox) は両 spec で一貫。**Status**: Resolved

## Resolved by user (grill gate)

### R1. "edit" の同期/非同期セマンティクス
決定: edit も非同期 AdminCommand に揃える。content mutation も Python 所有、UI は楽観反映 + pending→saved/failed。境界を2本化しない。#26 spec/design に反映済み。
**Status**: Resolved

### R2. AdminCommand idempotency_key / client token の発番層
決定: Admin API server が発番。client request-id 供給時のみ併用（任意）。#26 spec/design・#28 design に反映済み。
**Status**: Resolved
