# Storage Strategy

## Status

Accepted

## Context

SPAutoPost は、Advisory、DraftPost、ReviewEvent、Publication、AuditEvent を保存します。

M1 では Azure hosted core、Azure Container Apps / Jobs、Admin API / UI を含める方針です。そのため、M1 の hosted PoC では、複数の処理から共有できる database を使います。

## Decision

M1 の Azure hosted PoC では、Azure Database for PostgreSQL Flexible Server を採用します。

SQLite は local development、unit test、fixture verification、offline dry-run 用として残します。

## Rationale

- Admin API / UI と scheduled jobs が同じ state を共有する必要がある。
- Azure hosted PoC の運用形態に近い検証ができる。
- M1 から schema と migration を検証できる。
- 将来のデータ量増加や監査保持に備えやすい。
- 後から SQLite から PostgreSQL へ移行する手戻りを減らせる。

## Consequences

- #28 は PostgreSQL storage baseline に変更する。
- local/test では SQLite adapter を許容する。
- M1 hosted PoC の正本 DB は PostgreSQL とする。
- schema は PostgreSQL を基準に設計する。
- `DATABASE_URL` または同等の接続設定を導入する。

## Related

- Spec: docs/specs/architecture.md
- Spec: docs/specs/data-model.md
- Spec: docs/specs/configuration.md
- Issue: #3
- Issue: #28
