# Database Migration Strategy

## Status

Accepted

## Context

M1 hosted PoC では Azure Database for PostgreSQL Flexible Server を正本 DB とします。

Python core と TypeScript / Node.js Admin UI/API の両方が同じ schema を利用するため、どちらか一方の framework 固有 schema に寄せすぎない管理が必要です。

## Decision

DB schema の正本は SQL migration とします。

M1 では `db/migrations` 配下に migration baseline を置きます。

## Rationale

- Python と TypeScript / Node.js の両方から参照しやすい。
- PostgreSQL を正本 schema として明示できる。
- 将来の managed database 運用に移行しやすい。
- ORM に依存しすぎない。

## Consequences

- #28 で PostgreSQL schema と migration baseline を実装する。
- local/test SQLite adapter は、PostgreSQL schema と矛盾しない範囲で互換実装とする。
- Admin UI/API と Python core は同じ migration version を前提に動作する。

## Related

- Spec: docs/specs/m1-mvp-scope.md
- Spec: docs/specs/configuration.md
- Issue: #28
