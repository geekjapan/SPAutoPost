# Operation Runbook

## Status

Draft

## Purpose

この runbook は、SPAutoPost の日常運用、手動実行、dry-run、投稿確認、失敗時対応、再実行、停止手順を定義します。

## Operating Modes

### dry-run

実投稿せず、収集、正規化、原稿生成、投稿 payload preview、監査ログ確認を行う。

用途:

- 初回検証
- provider 変更後の確認
- SharePoint 投稿前確認
- 障害復旧後の確認

### draft posting

SharePoint に下書きまたはテスト投稿する。

用途:

- MVP 検証
- 掲示板担当者による事前確認

### publish

承認済み DraftPost を SharePoint に公開する。

MVP では既定無効。明示承認後のみ許可する。

## Daily Operation

1. 収集結果を確認する。
2. normalized advisory を確認する。
3. priority / urgency を確認する。
4. DraftPost を生成する。
5. validation warnings を確認する。
6. reviewer が原稿を確認する。
7. approved のみ SharePoint に投稿する。
8. Publication と AuditEvent を確認する。

## Manual Run Checklist

- [ ] config が正しい
- [ ] dry_run が意図した値である
- [ ] provider が意図したものになっている
- [ ] SharePoint target が test site または本番 site と一致している
- [ ] Secret が環境変数または secret store に存在する
- [ ] 入力 advisory が正しい

## Before Publishing

- [ ] DraftPost が approved
- [ ] validation error がない
- [ ] dangerous detail warning がない
- [ ] references がある
- [ ] urgency が妥当
- [ ] idempotency_key が既存 Publication と衝突していない、または update 意図が明確
- [ ] SharePoint target が正しい
- [ ] `docs/runbooks/production-hardening.md` の pre-production gate と security review が完了している

## Failure Response

### Log Analytics first check

Azure hosted runtime では、障害調査の最初に `correlation_id` を 1 つ決め、
`docs/runbooks/log-analytics.md` と `deploy/log-analytics.queries.kql` で
Container Apps / Jobs logs、AuditEvent、publication result を確認する。

確認する項目:

- job / app の直近 console logs
- Container Apps system logs の restart / failed execution
- `AuditEvent.correlation_id`
- `error_code`
- `publish_result` / `publish_create` / `publish_update` / `publish_dry_run`
- `idempotency_key`

### Source fetch failure

1. error_code を確認する。
2. rate limit / timeout の場合は retry/backoff を待つ。
3. auth failed の場合は credential / permission を確認する。
4. parser failed の場合は source format change を疑う。

### LLM provider failure

1. provider_config_invalid の場合は config を確認する。
2. provider_auth_failed の場合は Secret / permission を確認する。
3. provider_rate_limited の場合は backoff する。
4. output validation failed の場合は reviewer が手動確認する。

### SharePoint publish failure

1. Graph authorization を確認する。
2. target site/list/page ID を確認する。
3. required field missing を確認する。
4. idempotency_key と既存 Publication を確認する。
5. retry する場合は duplicate guard を通す。

## Re-run Policy

再実行前に確認する項目:

- 前回の Publication status
- idempotency_key
- SharePoint item/page ID
- error_code
- retryable

published の draft は原則 create 再実行しない。更新が必要な場合は update として扱う。

## Retry / Backoff / Rate Limit Policy

詳細な本番前確認と retry / backoff / rate limit policy は `docs/runbooks/production-hardening.md` を正本とします。運用時は、retry 前に error_code / retryable / idempotency_key / 既存 Publication / SharePoint item/page ID を確認します。

## Stop Procedure

緊急停止が必要な場合:

1. scheduler を停止する。
2. enable_sharepoint_publish を false にする。
3. allow_publish を false にする。
4. provider を mock または disabled にする。
5. pending publication を確認する。

## Correction Procedure

誤投稿が発生した場合:

1. SharePoint 上の投稿を確認する。
2. 必要に応じて非公開、修正、削除を実施する。
3. Publication status を corrected または failed equivalent として記録する設計を検討する。
4. 原因を AuditEvent と incident note に残す。
5. 重複投稿や誤情報の再発防止策を Issue 化する。

## Logs to Check

- source_fetch
- normalize
- draft_generate
- draft_validate
- review
- approve
- publish_result
- error

Azure hosted runtime の Log Analytics 確認手順は `docs/runbooks/log-analytics.md` を参照する。

## Related Specs

- docs/specs/security-baseline.md
- docs/specs/audit-log.md
- docs/specs/error-handling.md
- docs/specs/sharepoint-publishing.md
- docs/runbooks/log-analytics.md
