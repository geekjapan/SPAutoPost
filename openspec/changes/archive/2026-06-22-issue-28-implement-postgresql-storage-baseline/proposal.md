## Why

M1 hosted PoC では Admin UI/API と scheduled jobs が同じ state を共有するため、PostgreSQL を正本 DB とする storage baseline が必要になる（`storage-strategy.md`）。canonical entity（Advisory / DraftPost / ReviewEvent / Publication / AuditEvent）と、Admin↔Python core 境界を支える AdminCommand テーブルを一度に先出しすることで、下流 Issue（#6/#7/#8/#10/#31/#33/#36）が同じ schema を read-only 前提で並列実装できる土台を作る。

## What Changes

- 新 capability `storage` を導入し、canonical entity の永続化を定義する。
- PostgreSQL schema と SQL migration baseline を `db/migrations` 配下に置く（`db-migration-strategy.md` に従い SQL migration を schema 正本とする）。
- Python 所有の storage port を定義する（entity read/write stores と AdminCommand 用 command queue 操作）。
- ADR `admin-core-boundary.md` 由来の `AdminCommand`/Intent テーブルを追加する（非同期 command handoff の受け皿）。
- local/test 用 SQLite adapter を、PostgreSQL schema と矛盾しない互換実装として提供する。
- `idempotency_key` を Publication と AdminCommand の2スコープで UNIQUE 制約する。

## Capabilities

### New Capabilities
- `storage`: canonical entity（SourceRecord, Advisory, DraftPost, ReviewEvent, Publication, AuditEvent）と AdminCommand の永続化、Python 所有 storage port、PostgreSQL 正本 schema + SQL migration baseline、local/test 用 SQLite 互換 adapter、idempotency 制約。

### Modified Capabilities
<!-- 既存 capability spec は未作成のため、変更対象なし。 -->

## Impact

- 新規: `db/migrations/`（SQL migration baseline）、`src/storage/`（port + PostgreSQL adapter + SQLite adapter）、`src/models/`（canonical entity 定義）。
- 依存: PostgreSQL driver（例: psycopg）、SQLite（stdlib）、migration 実行ツール（Alembic は実行/wrap のみ、schema 正本にはしない）、`DATABASE_URL` 等の接続設定（`configuration.md`）。
- 正本参照: `docs/specs/data-model.md`、`docs/specs/architecture.md`、ADR `admin-core-boundary.md` / `storage-strategy.md` / `db-migration-strategy.md`。
- 非対象: 本番 DB 運用設計の完全確定、高度な並行実行制御、本番監視、Microsoft Graph 認証（#27）、Entra role mapping（#29）。Secret は保存しない（`data-model.md` Sensitive Data Policy）。
