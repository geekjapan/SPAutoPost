## Why

Issue #30 では、M6 Production Hardening として Azure hosted runtime のログ確認、監査追跡、障害調査、redaction 確認を運用手順に落とす必要がある。既存 Spec は `AuditEvent`、`correlation_id`、`error_code`、Publication result、Secret ログ禁止を定義済みなので、本 change は実 Azure tenant 固有の provisioning ではなく、Log Analytics で確認する最小の診断設定・KQL・runbook を追加する。

## What Changes

- Container Apps / Container Apps Jobs の console/system logs を Log Analytics workspace へ送る diagnostic settings の最小確認項目を定義する。
- `AuditEvent` JSON log line を `correlation_id`、`error_code`、Publication result で検索する KQL snippets を追加する。
- Secret / token / authorization header が Log Analytics に送信されていないことを確認する redaction query を追加する。
- 運用 runbook と security review checklist に Log Analytics 確認手順を追記する。
- workspace ID、resource group、alert threshold、dashboard 配置など tenant 固有値は手順上の manual step とし、実値や本番 IaC は追加しない。

## Capabilities

### New Capabilities

- `log-analytics-integration`: Azure Container Apps / Jobs logs、AuditEvent tracking、error/publication result search、redaction confirmation の最小運用確認を扱う。

### Modified Capabilities

- なし。

## Impact

- `deploy/README.md`
- `deploy/jobs.example.yaml`
- `deploy/log-analytics.queries.kql`
- `docs/runbooks/log-analytics.md`
- `docs/runbooks/operation.md`
- `docs/runbooks/security-review.md`
- `docs/specs/audit-log.md`
- `openspec/changes/issue-30-add-azure-log-analytics-integration/`
