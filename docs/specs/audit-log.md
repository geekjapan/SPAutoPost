# Audit Log Specification

## Status

Approved

## Purpose

この Spec は、SPAutoPost の収集、正規化、AI 作文、レビュー、承認、SharePoint 投稿、失敗時対応を追跡するための監査ログ要件を定義します。

## Goals

- 投稿根拠を追跡できる。
- どの情報源に基づいて、どの AI provider / prompt version が原稿を生成したか分かる。
- 誰がレビュー・承認したか分かる。
- SharePoint へいつ、どの対象に、どの結果で投稿したか分かる。
- Secret や不要な個人情報をログに出さない。

## AuditEvent Model

### Minimum Required Fields

すべての監査イベントに以下 5 フィールドが必須（SHALL）:

| フィールド | 型 | 説明 |
|---|---|---|
| `audit_event_id` | UUID | イベント一意識別子 |
| `event_type` | enum | イベント種別（下記 Event Types 参照） |
| `correlation_id` | string | 一連処理の追跡 ID |
| `result` | enum (success / failure / skipped / warning) | 処理結果 |
| `created_at` | ISO 8601 UTC | イベント発生日時 |

これら 5 フィールドのいずれかが欠けている場合、監査ログへの記録を拒否する。

### Recommended Fields

推奨項目（必須 5 フィールドに加えて記録を推奨）:

- actor
- service_principal
- related_ids
- source_name
- provider_name
- provider_type
- prompt_version
- target_site_id
- target_list_id
- target_page_id
- sharepoint_item_id
- sharepoint_page_id
- idempotency_key
- error_code
- error_message

## Event Types

- source_fetch
- source_parse
- normalize
- triage
- draft_generate
- draft_validate
- review
- approve
- reject
- regenerate
- publish_dry_run
- publish_create
- publish_update
- publish_result
- error

## Correlation ID

一連の処理を追跡するため、correlation_id を付与します。

推奨単位:

- 1 回の実行単位
- 1 draft generation 単位
- 1 publication attempt 単位

## Logging Prohibition

次をログに出してはいけません。

- API key
- access token
- refresh token
- client secret
- certificate private key
- cookie
- authorization header
- raw prompt に含まれる機微情報
- 不要な個人情報

## Prompt and Output Logging

MVP では、prompt 全文と LLM 出力全文の保存は慎重に扱います。

推奨:

- prompt_version を保存する。
- generation_input_hash を保存する。
- LLM 出力本文は DraftPost として保存する。
- raw prompt 全文をログへ直接出力しない。
- 保存が必要な場合は、保存先、保持期間、閲覧権限を別途定義する。

## Retention

初期方針:

- 開発環境: 短期保持でよい。
- 本番環境: 組織の監査要件に合わせる。
- Secret を含む可能性があるログは保存しない。

保持期間は本番投入前に確定します。

## Failure Audit

失敗時に記録する項目:

- operation
- error_code
- retryable
- failure_count
- target
- correlation_id
- created_at

例:

- source_rate_limited
- provider_timeout
- output_validation_failed
- graph_authorization_failed
- duplicate_detected

## Review Audit

review / approval に記録する項目:

- draft_id
- reviewer
- action
- previous_status
- next_status
- comment
- validation_warnings
- created_at

## Related Issues

- #5 Define security, secrets, audit, and compliance baseline
- #10 Implement dry-run preview and minimal audit log
- #19 Implement review and approval workflow
- #22 Production hardening runbook, observability, and security review
