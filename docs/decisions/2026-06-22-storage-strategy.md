# Storage Strategy

## Status

Accepted

## Context

SPAutoPost は、Advisory、DraftPost、ReviewEvent、Publication、AuditEvent を保存します。

MVP ではデータ量が限定的であり、まずは実装速度、ローカル検証、スキーマ確認、dry-run、移行容易性を重視します。一方で、将来的に定期収集、管理 UI/API、複数ジョブ、監査保持が進むと、managed database への移行が必要になる可能性があります。

## Decision

MVP のデータベースは SQLite とします。

データ量、同時実行、バックアップ、監査保持、複数インスタンス運用の要件が増えてきた段階で、Azure managed database へ移行します。

移行候補:

- Azure SQL Database
- PostgreSQL-compatible managed database
- Azure Storage / Table Storage

## Rationale

- MVP の実装と検証が速い。
- Python CLI / Batch と相性がよい。
- ローカル開発と Azure Container Apps Jobs の entrypoint 検証がしやすい。
- 将来移行に備えて schema を明示的に管理すれば、初期の過剰設計を避けられる。

## Consequences

- MVP では SQLite schema を設計対象に含める。
- DB migration 管理を早期に導入する。
- Azure hosted runtime で SQLite を扱う場合、永続化、バックアップ、同時実行、ジョブ多重起動に注意する。
- managed database への移行条件を M6 または運用拡大時に再評価する。

## Related

- Spec: docs/specs/architecture.md
- Spec: docs/specs/data-model.md
- Issue: #3
- Issue: #23
