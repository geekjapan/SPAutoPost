# External Collector Boundary Specification

## Status

Proposed

## Purpose

この Spec は、将来的に crawler / collector / 情報整理機能を SPAutoPost から分離する場合の責務境界、import schema、実行方式、失敗時動作を定義します。

## Boundary Principle

SPAutoPost は最終的に「正規化済みセキュリティ情報を社内掲示板向けに作文・レビュー・投稿する基盤」として責務を絞ります。

外部化可能な責務:

- crawling
- scraping
- feed polling
- source-specific parsing
- threat intelligence enrichment
- asset inventory matching

SPAutoPost に残す責務:

- normalized advisory import
- draft composition
- human review
- SharePoint publishing
- audit log
- duplicate post guard

## Import Modes

### file import

MVP 以降の基本方式。

- JSON
- YAML
- directory batch
- signed artifact optional

### API import

将来方式。

- authenticated HTTP API
- schema validation
- idempotent import

### queue import

将来方式。

- queue / topic
- event-driven import
- dead-letter queue

## Import Schema

最小 schema:

```json
{
  "schema_version": "1.0",
  "producer": "collector-name",
  "generated_at": "2026-01-01T00:00:00Z",
  "correlation_id": "optional",
  "advisories": [
    {
      "advisory_id": "optional-external-id",
      "title": "...",
      "summary": "...",
      "cve_ids": [],
      "jvn_ids": [],
      "affected_products": [],
      "severity": "unknown",
      "references": []
    }
  ]
}
```

## Validation

import 時に検査する項目:

- schema_version
- producer
- generated_at
- advisory title
- references
- allowed enum values
- URL format
- duplicate key

invalid record は隔離し、全体処理を止めるかどうかは mode で制御します。

## Idempotency

import の重複を避けるため、次を使います。

- producer
- external advisory_id
- cve_ids / jvn_ids
- source URL
- raw hash

## Security

- external collector からの入力は信頼しない。
- schema validation を必須にする。
- HTML / markdown injection を考慮する。
- imported text をそのまま SharePoint に出さず、Draft Composition と Review を通す。
- API import では認証・認可を必須にする。

## Audit Requirements

記録する項目:

- producer
- schema_version
- import mode
- record count
- accepted count
- rejected count
- duplicate count
- correlation_id
- error code

## Related Issues

- #13 Define KEV and vendor advisory adapter interface
- #21 Add scheduler and external collector import boundary
- #22 Production hardening runbook, observability, and security review
