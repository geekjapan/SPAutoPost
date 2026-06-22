# Log Analytics Timing

## Status

Accepted

## Context

SPAutoPost は Azure hosted core を前提にし、定期収集、記事生成、管理者レビュー、SharePoint 投稿、監査ログを扱います。

本番運用では Azure Log Analytics 連携が有用ですが、MVP ではまず app-level audit log、correlation_id、error_code、Publication / DraftPost / AuditEvent の追跡を優先します。

## Decision

Azure Log Analytics 連携は M6 Production Hardening で扱います。

MVP では、アプリケーション内の AuditEvent と error handling を実装します。

## Rationale

- MVP では縦串、記事生成、レビュー、SharePoint 投稿の実現が優先。
- Log Analytics 連携を M1 に含めると、MVP の実装範囲が重くなる。
- 監査ログの論理モデルを先に固めれば、後から Log Analytics へ送る設計に移行しやすい。

## Consequences

- M1 では app-level audit log を実装する。
- Log Analytics workspace、diagnostic settings、query、alert は M6 で扱う。
- M6 の runbook / security review で Log Analytics 連携を確認する。

## Related

- Spec: docs/specs/audit-log.md
- Spec: docs/specs/architecture.md
- Issue: #10
- Issue: #22
