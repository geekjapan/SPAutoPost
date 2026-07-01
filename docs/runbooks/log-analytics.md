# Azure Log Analytics Runbook

## Status

Draft

## Purpose

この runbook は、Azure Container Apps / Container Apps Jobs 上の SPAutoPost について、Log Analytics でログ収集、AuditEvent 追跡、障害調査、redaction 確認を行う最小手順を定義します。

## Scope

対象:

- Container Apps Admin API app の console / system logs
- Container Apps Jobs の console / system logs
- `AuditEvent` JSON log line の `correlation_id` 検索
- `error_code` / publication result 検索
- Secret / token が送信されていないことの確認

非対象:

- SIEM 連携の本格設計
- SOC 運用設計
- tenant 固有の alert action group / dashboard ID / workspace ID のコミット
- Azure リソースの自動 provision

## Manual Azure Setup Boundary

次の値は tenant / subscription 固有のため、リポジトリに実値を保存しません。

- Log Analytics workspace resource ID
- Container Apps Environment resource ID
- diagnostic setting name
- alert rule / action group / dashboard IDs
- resource group / subscription ID

operator は Azure Portal、Azure CLI、Bicep など組織標準の方法で Container Apps Environment の diagnostic settings を有効化し、console logs と system logs を選択した Log Analytics workspace に送信します。

## Diagnostic Settings Confirmation

1. Container Apps Environment の diagnostic settings が Log Analytics workspace を宛先にしていることを確認する。
2. console logs と system logs が有効であることを確認する。
3. `deploy/log-analytics.queries.kql` の「Confirm recent Container Apps / Jobs console logs」を実行する。
4. Admin API app と scheduled job のログが 24 時間以内に取得できることを確認する。

## AuditEvent Tracking

障害調査では、まず `correlation_id` を 1 つ決めて追跡します。

取得元:

- Admin API response
- AuditEvent table / export
- incident note
- failed job log

確認手順:

1. `deploy/log-analytics.queries.kql` の「Trace AuditEvent entries by correlation_id」に `correlationId` を設定する。
2. `event_type`、`result`、`error_code`、`operation`、`publication_id`、`draft_id` を時系列で確認する。
3. SharePoint 投稿調査では `publication_id`、`sharepoint_page_id`、`idempotency_key` を incident note に記録する。

## Error and Publication Result Search

`error_code` が分かっている場合は「Search error_code values across AuditEvent log lines」を使います。

publication result の一覧確認では「Search publication result events」を使います。

確認項目:

- `publish_dry_run` / `publish_create` / `publish_update` / `publish_result`
- `result` が `success` / `failure` / `skipped` / `warning` のどれか
- `error_code`
- `operation`
- `idempotency_key`
- `sharepoint_page_id`

## Redaction Confirmation

security review または本番前確認では、`deploy/log-analytics.queries.kql` の「Redaction / no-token confirmation」を実行します。

期待結果:

- access token が出ない
- refresh token が出ない
- client secret が出ない
- authorization header が出ない
- cookie が出ない
- private key が出ない
- raw API key が出ない

hit がある場合は、placeholder や false positive と証明できるまで security finding として扱います。実 Secret の可能性がある場合は、ログ保全範囲を限定し、credential rotation と incident response を開始します。

## Alert and Dashboard Minimal Recommendation

alert / dashboard は tenant 固有設定のため、この repository では provision しません。

M6 の最小推奨:

- Container Apps Jobs の failed execution count
- `AuditEvent.result == failure`
- `error_code` の急増
- redaction query hit count > 0

しきい値、通知先、action group は運用組織が決定し、Issue または decision record に記録します。

## Related

- Issue #30
- OpenSpec change `issue-30-add-azure-log-analytics-integration`
- `deploy/log-analytics.queries.kql`
- `docs/runbooks/operation.md`
- `docs/runbooks/security-review.md`
- `docs/specs/audit-log.md`
