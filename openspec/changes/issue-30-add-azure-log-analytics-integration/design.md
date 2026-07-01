## Context

既存 Spec は `AuditEvent`、`correlation_id`、`error_code`、Publication result、Secret ログ禁止を定義済み。Issue #30 は M6 の運用監視として、Azure Container Apps / Jobs の Log Analytics 確認手順を追加する change であり、tenant 固有の Azure provision は含めない。

## Goals / Non-Goals

**Goals:**

- Container Apps / Jobs logs を Log Analytics で確認する手順を示す。
- `AuditEvent` を `correlation_id`、`error_code`、publication result で検索する KQL snippets を用意する。
- Secret / token / authorization header が送信されていないことを確認する query を用意する。
- operation / security runbook に確認手順を入れる。

**Non-Goals:**

- Log Analytics workspace、diagnostic settings、alert、dashboard の本番 provision。
- tenant 固有 resource ID、workspace ID、action group、dashboard ID の repository 保存。
- アプリケーションコード変更。
- SIEM / SOC の本格設計。

## Decisions

### Decision: docs and query snippets only

Issue #30 の受け入れ条件は「確認方法」「追跡できる」「検索できる」「確認している」「runbook 追記」であり、実 Azure resource 作成は tenant 判断を伴う。したがって、この change は `docs/runbooks/log-analytics.md` と `deploy/log-analytics.queries.kql` を主成果物にする。

Alternative considered: Bicep / Terraform を追加する。workspace、diagnostic destination、alert 通知先が tenant 固有で、Issue の最小範囲を超えるため採用しない。

### Decision: AuditEvent JSON log line query path

Log Analytics 側では Container Apps console logs から `AuditEvent` JSON line を検索する前提の KQL を定義する。既存 AuditEvent model をそのまま使い、新しい schema や dependency は追加しない。

Alternative considered: custom table ingestion を前提にする。追加 collector / ingestion pipeline が必要になり、Issue #30 の最小 scope を超えるため採用しない。

## Risks / Trade-offs

- [Risk] 実 Azure 環境の table / column が tenant 設定や platform version で差分を持つ → `column_ifexists()` を使い、runbook で operator 確認手順として扱う。
- [Risk] AuditEvent が console log に出ていない環境では KQL が空になる → app-level AuditEvent の保存は既存正本で、Log Analytics への出力確認は M6 運用設定の manual step とする。
- [Risk] redaction query が false positive を返す → placeholder / false positive と証明できるまで security finding として扱う。

## Migration Plan

1. Azure operator が Container Apps Environment diagnostic settings を有効化する。
2. `deploy/log-analytics.queries.kql` で console / system logs を確認する。
3. production-like run 後に `correlation_id`、`error_code`、publication result、redaction query を実行する。
4. alert / dashboard が必要な場合は、tenant 側の運用標準に従い Issue または decision record に記録する。

Rollback は不要。repository 変更は docs / query snippets のみ。
