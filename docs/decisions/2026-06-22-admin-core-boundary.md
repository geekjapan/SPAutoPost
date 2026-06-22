# Admin UI/API ↔ Python core boundary

## Status

Accepted

## Context

SPAutoPost は polyglot 構成（`architecture.md`）。Python core が Storage Port・Review/Approval State machine・Publisher・Audit を所有し、TypeScript/Node.js Admin UI/API が Entra ログイン・DraftPost 一覧/詳細/修正・approve/reject/request-regeneration・publish request・audit 参照を担う。両者は単一の Azure PostgreSQL を共有する。

`architecture.md` の Open Question「Admin UI/API と Python core の呼び出し境界を process / HTTP / shared DB のどれにするか」が未決で、#26（境界 Spec）・#28（storage baseline）・#31（Admin API skeleton）の設計を縛っていた。`admin-api-ui-in-m1.md` も「最小 API を Python 側で先に実装するかは #26 で決める」と保留していた。

## Decision

M1 の境界を **「read は shared DB 直読み / state 遷移 write は intent-table 経由の非同期 command」** とする。

- **Read**: Admin API(TS) は Postgres から DraftPost / ReviewEvent / AuditEvent を直接読む（一覧・詳細・audit 参照）。
- **Write（状態遷移）**: TS は auth/RBAC とリクエスト形式 validation のみ行い、ドメイン状態は触らない。idempotent な `AdminCommand` 行を1件 insert して `accepted/pending` を返す。
- **処理**: Python job/CLI が pending command を消費し、edit / approve / reject / request-regeneration / publish-request の状態遷移・validation・ReviewEvent・AuditEvent を実行する。ドメイン状態の write は Python の transition 関数の背後に置き、generic な TS repository から触らせない。
- **Reviewer UX**: 非同期（accepted/pending）。UI は `pending → succeeded/failed` を後から表示する。同期成功/失敗フィードバックは M1 非対象。
- **M1 では long-running Python HTTP サービスを作らない。** 遷移保護は queued command で表現できるため。

### #28 storage baseline への影響

canonical models（Advisory / DraftPost / ReviewEvent / Publication / AuditEvent）を先出しし、加えて `AdminCommand`/Intent テーブルを含める。

- columns: `command_id, command_type, target_draft_id, requested_by(principal/roles), payload(JSON), idempotency_key(unique index), status(pending|processing|succeeded|failed|cancelled), error_code, error_message, correlation_id, created_at, processed_at`
- storage port: `append_command`, `claim_pending_commands`（トランザクショナル; PostgreSQL は `SKIP LOCKED`, SQLite は simple）, `complete_command` / `fail_command`, および entity read stores。

## Rationale

- Python core が所有する状態機械を単一の真実に保ち、遷移ロジックを TS に二重実装しない。
- queued command が「approved でないと publish できない」等の遷移保護を表現でき、long-running runtime を足す価値がない（M1 lazy）。
- 下流 Issue（#6/#7/#8/#10/#33/#36）が canonical models に read-only になり、衝突なしの並列ファンアウトが可能になる。
- Opus 4.8（author）× GPT-5.5（adversarial review）の cross-model discussion（agmsg, 2026-06-22）で round 1 収束。GPT-5.5 が intent-table を Python-owned command 表として具体化し、port メソッドと SKIP LOCKED を提案した。

## Consequences

- #28 scope = 5 canonical models + `AdminCommand` テーブル + 上記 port メソッド。schema/migration を含むため **直列・単一ワーカー**で実装する。
- #26 境界 Spec = 本 ADR を反映。#31 Admin API は write を command enqueue に限定し、read は直読み。
- 以下は #28 をブロックしない（command テーブルの `requested_by` 等で吸収）。HUMAN-GAP として別 Issue で継続:
  - #27 Microsoft Graph 認証方式（publisher service identity・audit fields に影響）
  - #29 Entra role mapping（group vs app role）

## Related

- `docs/specs/architecture.md`（Open Question を解消）
- `docs/decisions/2026-06-22-admin-api-ui-in-m1.md`（保留点を解決）
- `docs/decisions/2026-06-22-storage-strategy.md` / `2026-06-22-db-migration-strategy.md`
- Issues: #26, #28, #31, #27, #29
