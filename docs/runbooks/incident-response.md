# Incident Response Runbook

## Status

Draft

## Purpose

この runbook は、SPAutoPost の運用中に誤投稿、重複投稿、誤情報掲載、Secret 漏えい、外部 API 障害などが発生した場合の初動対応を定義します。

## Incident Types

- wrong_post: 誤った内容を SharePoint に投稿した
- duplicate_post: 同じ内容を重複投稿した
- unauthorized_post: 承認されていない draft が投稿された
- sensitive_data_post: 機微情報を投稿した
- incorrect_ai_output: AI 生成文に誤情報が含まれていた
- secret_exposure: Secret が repo / log / SharePoint に露出した
- provider_misuse: 規約・運用方針に反する provider 利用があった
- source_corruption: 収集元または外部 collector 入力が不正だった

## Initial Response

1. 影響範囲を確認する。
2. SharePoint 投稿を非公開化、修正、削除する必要があるか判断する。
3. scheduler / publish 機能を停止する。
4. correlation_id、draft_id、publication_id、SharePoint item/page ID を記録する。
5. 関連ログと AuditEvent を保全する。
6. 必要に応じて関係者に連絡する。

## Emergency Stop

```text
enable_sharepoint_publish=false
allow_publish=false
scheduler=disabled
provider=mock or disabled
```

設定変更後、pending publication が残っていないか確認します。

## Wrong Post

1. SharePoint 上の投稿 URL / item ID / page ID を確認する。
2. 内容を修正、非公開、削除のいずれかで対応する。
3. 正しい内容の再投稿が必要か判断する。
4. DraftPost / Publication の状態を確認する。
5. 原因を分類する。

原因例:

- source data error
- AI output error
- review miss
- approval error
- wrong target
- idempotency failure

## Duplicate Post

1. 重複した SharePoint 投稿を特定する。
2. 残す投稿と削除/非公開にする投稿を決める。
3. idempotency_key と Publication を確認する。
4. retry / backoff / duplicate guard の不備を Issue 化する。

## Sensitive Data Exposure

1. 公開範囲を確認する。
2. SharePoint 投稿、log、repository から露出箇所を特定する。
3. Secret の場合は即時 revoke / rotate する。
4. 影響範囲と閲覧可能者を確認する。
5. 再発防止策を Issue 化する。

## Incorrect AI Output

1. 問題のある DraftPost と出典を確認する。
2. SharePoint 投稿を修正または取り下げる。
3. AI output validation の warning を確認する。
4. prompt template / validation rule / review checklist の改善を Issue 化する。

## Evidence to Preserve

- AuditEvent
- DraftPost
- Publication
- source records
- prompt_version
- generation_input_hash
- reviewer comments
- approval event
- SharePoint item/page ID
- error logs

Secret そのものは証跡として保存しません。必要な場合は hash または secret identifier を記録します。

## Post-Incident Review

記録項目:

- incident date
- detected by
- affected post
- affected users or audience
- root cause
- corrective action
- preventive action
- related issues
- accepted risk if any

## Related Specs

- docs/specs/security-baseline.md
- docs/specs/audit-log.md
- docs/specs/error-handling.md
- docs/specs/sharepoint-publishing.md
