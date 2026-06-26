# Canonical Data Model Specification

## Status

Accepted for M0

canonical な advisory / draft / publication / audit データモデルは Issue #3 の OpenSpec change で確定・merge 済み。multi-source `source_refs` の baseline 化（#28）と `event_type` enum の権威付け（`audit-log.md` 経由、#10）は将来 migration として deferred。詳細は `docs/design-documents.md` の Review & Status Matrix (Issue #23) を参照。

## Purpose

この Spec は、SPAutoPost が扱う脆弱性情報、掲示板原稿、投稿結果、監査ログの正規化データモデルを定義します。

## Design Principles

- 情報源ごとの差異を Advisory に集約する。
- AI 作文と SharePoint 投稿を DraftPost / Publication として分離する。
- 生成 AI の入力、出力、prompt version、provider を追跡可能にする。
- 投稿処理は idempotency_key を持ち、重複投稿を防ぐ。
- 将来の external collector 分離後も、normalized advisory import で継続利用できるようにする。

## Entity Overview

```text
SourceRecord
  -> Advisory
       -> DraftPost
            -> ReviewEvent
            -> Publication
                 -> AuditEvent
```

## SourceRecord

外部情報源または手動入力から取得した生データの記録です。

必須項目:

- source_record_id: string
- source_type: manual | nvd | myjvn | kev | vendor | rss | external_collector | web_scrape
- source_name: string
- source_url: string optional
- retrieved_at: datetime
- raw_hash: string
- parser_version: string

任意項目:

- raw_payload_ref
- http_status
- etag
- last_modified
- error_code
- error_message

## Advisory

脆弱性またはセキュリティ注意喚起を表す正規化データです。

> **source_refs の baseline 実装について（reconcile note / Issue #28）**
> 概念モデルでは `source_refs: SourceRef[]`（情報源ごとの `source_record_id` /
> `source_name` / `source_url` / `retrieved_at` / `confidence` を持つ配列）を必須としている。
> ストレージ baseline（`db/migrations/{postgres,sqlite}/0001_baseline.sql` と
> `src/spautopost/storage/models.py` の `Advisory` DTO）では、当面の収集系が単一情報源を
> 主とすることから、これを `advisories.source_record_id`（`source_records` への nullable FK 1 本）
> へ意図的に縮退している。複数情報源・per-source confidence が必要になった時点で、
> `source_refs` を JSONB 列（両方言）または `advisory_source_refs` junction テーブルとして
> 追加 migration で導入し、本ノートを更新する。YAGNI に基づく延期であり、概念モデルの
> 正本性は維持する。

必須項目:

- advisory_id: string
- title: string
- summary: string
- source_refs: SourceRef[]
- references: Reference[]
- published_at: datetime optional
- updated_at: datetime optional
- created_at: datetime
- normalized_at: datetime

推奨項目:

- cve_ids: string[]
- jvn_ids: string[]
- vendor_advisory_ids: string[]
- affected_products: AffectedProduct[]
- affected_versions: string[]
- severity: critical | high | medium | low | unknown
- cvss_version: string optional
- cvss_score: number optional
- cvss_vector: string optional
- exploit_status: confirmed | likely | unknown | none
- kev_status: listed | not_listed | unknown
- patch_available: true | false | unknown
- mitigation: string optional
- workaround: string optional
- source_confidence: high | medium | low | unknown
- tags: string[]

## SourceRef

Advisory の根拠となる情報源です。

- source_record_id: string
- source_name: string
- source_url: string optional
- retrieved_at: datetime
- confidence: high | medium | low | unknown

## Reference

掲示板本文に表示可能な参考情報です。

- label: string
- url: string
- type: vendor | nvd | jvn | kev | advisory | patch | other

## AffectedProduct

影響を受ける製品・サービスです。

- vendor: string optional
- product: string
- version_range: string optional
- platform: string optional
- internal_relevance: confirmed | suspected | unknown | not_applicable

## DraftPost

SharePoint 掲示板向けの原稿です。

必須項目:

- draft_id: string
- advisory_ids: string[]
- title: string
- audience: general_users | administrators | mixed
- urgency: emergency | high | normal | low
- summary_for_users: string
- impact: string
- required_actions: string[]
- references: Reference[]
- status: DraftStatus
- created_at: datetime
- updated_at: datetime

推奨項目:

- admin_actions: string[]
- deadline: datetime optional
- generated_by_provider: string
- provider_type: production_api | production_flow | generic_api | test_mock | test_manual
- prompt_version: string
- generation_input_hash: string
- validation_warnings: string[]
- reviewer: string optional
- review_comments: string[]

## DraftStatus

```text
created
generated
review_requested
reviewed
approved
rejected
regeneration_requested
publishing
published
failed
cancelled
```

## ReviewEvent

レビューと承認の履歴です。

- review_event_id: string
- draft_id: string
- reviewer: string
- action: request_review | comment | approve | reject | request_regeneration
- comment: string optional
- created_at: datetime

## Publication

SharePoint 投稿の結果です。

必須項目:

- publication_id: string
- draft_id: string
- target_type: list-item | site-page
- target_site_id: string
- publication_status: pending | dry_run | publishing | published | failed | skipped
- idempotency_key: string
- created_at: datetime
- updated_at: datetime

推奨項目:

- target_list_id: string optional
- target_page_library_id: string optional
- sharepoint_item_id: string optional
- sharepoint_page_id: string optional
- operation: dry-run | create | update | publish
- published_at: datetime optional
- error_code: string optional
- error_message: string optional
- retryable: boolean optional

## AuditEvent

監査・障害対応・説明責任のためのイベントです。

- audit_event_id: string
- event_type: source_fetch | normalize | draft_generate | validate | review | approve | publish | error
- correlation_id: string

> **event_type の正本について（reconcile note / Issue #28）**
> 上記の 8 値リストは概念例示であり、列挙の**正本は `docs/specs/audit-log.md` の「Event Types」（15 値）**である。
> ストレージ baseline migration（`db/migrations/{postgres,sqlite}/0001_baseline.sql`）の
> `audit_events.event_type` CHECK 制約は audit-log.md の 15 値
> （source_fetch, source_parse, normalize, triage, draft_generate, draft_validate, review,
> approve, reject, regenerate, publish_dry_run, publish_create, publish_update, publish_result, error）
> に一致させている。新しい event_type を追加する際は audit-log.md を更新し、両方言の migration を
> 同時に更新すること。
- actor: string optional
- service_principal: string optional
- related_ids: object
- result: success | failure | skipped | warning
- error_code: string optional
- message: string optional
- created_at: datetime

## ID and Hash Policy

- ID は実装言語に依存しない文字列とする。
- 外部 ID が存在する場合でも、内部 ID を別途持つ。
- generation_input_hash は、AI に渡した正規化済み入力から生成する。
- raw_hash は raw payload から生成する。
- idempotency_key は投稿先と draft の組み合わせから生成する。

## Sensitive Data Policy

データモデルに Secret を保存しません。

保存禁止:

- API key
- access token
- refresh token
- client secret
- private key
- cookie
- authorization header

## Related Issues

- #3 Define canonical advisory, draft, and publication data model
- #10 Implement dry-run preview and minimal audit log
- #20 Implement SharePoint publish idempotency and state tracking
