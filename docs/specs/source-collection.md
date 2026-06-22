# Source Collection Specification

## Status

Proposed

## Purpose

この Spec は、SPAutoPost が脆弱性情報、セキュリティアップデート、注意喚起を収集する際の情報源、adapter interface、差分取得、失敗時動作、出典保持を定義します。

## Source Types

初期対象:

- manual
- NVD
- MyJVN / JVN iPedia
- CISA KEV または KEV 相当情報
- vendor advisory
- RSS / Atom feed
- external collector import

## SourceAdapter Interface

推奨 interface:

```text
SourceAdapter.validateConfig(config) -> AdapterStatus
SourceAdapter.fetch(query) -> SourceRecord[]
SourceAdapter.normalize(record) -> Advisory[]
```

query 例:

- cve_id
- jvn_id
- vendor
- product
- published_from
- published_to
- modified_from
- modified_to
- severity

## Manual Source

MVP では手動入力を必須とします。

入力形式:

- YAML
- JSON

必須項目:

- title
- summary
- references

推奨項目:

- cve_ids
- jvn_ids
- affected_products
- severity
- mitigation
- published_at
- updated_at

## NVD Adapter

目的:

- CVE 情報を取得し、Advisory に正規化する。

取得方式:

- CVE ID 指定
- published / modified date range
- pagination

保持する情報:

- CVE ID
- description
- CVSS
- CPE / affected products if available
- references
- published / modified time

注意:

- rate limit に配慮する。
- API error 時は retryable を判定する。
- 取得結果は SourceRecord として raw hash を保持する。

## MyJVN Adapter

目的:

- 日本語の脆弱性対策情報を取得し、Advisory に正規化する。

取得候補:

- overview list
- detail info

保持する情報:

- JVN ID
- CVE ID
- title
- summary
- affected products
- impact
- solution / workaround
- references

注意:

- 出典表示要件を確認する。
- 日本語本文を Draft Composition に活用する。

## KEV Adapter

目的:

- 悪用確認済み脆弱性の判定に使う。

保持する情報:

- CVE ID
- vendor / product
- known exploited status
- due date if available
- action / mitigation if available
- source URL

## Vendor Advisory / RSS Adapter

目的:

- ベンダー固有のセキュリティ更新情報を取り込む。

初期方針:

- まず adapter interface と fixture を作る。
- 個別 vendor adapter は必要に応じて追加する。
- RSS/Atom は title / URL / published_at / summary を SourceRecord 化する。

## External Collector Import

将来 crawler / collector を外部化する場合、SPAutoPost は normalized advisory import を受け取ります。

最小 schema:

```json
{
  "schema_version": "1.0",
  "producer": "collector-name",
  "generated_at": "2026-01-01T00:00:00Z",
  "advisories": []
}
```

## Fetch State

差分取得のため、source ごとに state を保持します。

- source_name
- last_successful_fetch_at
- last_cursor
- last_etag
- last_modified
- failure_count

## Failure Handling

代表的な失敗:

- source_auth_failed
- source_rate_limited
- source_timeout
- source_unavailable
- source_response_invalid
- parser_failed
- normalization_failed

retry policy:

- rate limit: backoff
- timeout: retryable
- invalid response: non-retryable または parser issue
- auth failed: non-retryable

## Audit Requirements

記録する項目:

- source_name
- query
- retrieved_at
- result count
- failure count
- error code
- raw hash
- parser version

## Related Issues

- #7 Implement manual advisory input and validation
- #11 Implement NVD adapter
- #12 Implement MyJVN adapter
- #13 Define KEV and vendor advisory adapter interface
- #21 Add scheduler and external collector import boundary
