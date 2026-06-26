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
- web_scrape (Firecrawl adapter、M1 optional)

## SourceAdapter Interface

実装上の共通 interface:

```text
SourceAdapter.validate_config() -> AdapterStatus
SourceAdapter.fetch(query) -> SourceDocument[]
SourceAdapter.normalize(document) -> Advisory[]
```

`SourceDocument` は `SourceRecord` と raw payload を束ねる一時 DTO です。`SourceRecord`
は取得元、取得時刻、source URL、raw hash、parser version を保持し、raw payload
そのものは storage DTO に直接入れません。

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

責務境界:

- adapter は fetch / parse / normalize を担当し、storage への保存は呼び出し側が行う。
- fixture adapter は外部通信を行わず、下流 Issue の adapter 実装と test data の契約を固定する。
- live network client、API key、rate limit retry、crawler 本体は source-specific Issue で扱う。
- `SourceRecord.raw_hash` は raw payload の deterministic JSON hash とする。
- `Advisory.tags` は schema 変更なしに KEV status、source confidence、vendor/product hint を伝える補助 metadata として使う。

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

fixture 正規化では、CISA KEV catalog の JSON/CSV 由来の代表 field
（`cveID`, `vendorProject`, `product`, `vulnerabilityName`, `dateAdded`,
`shortDescription`, `requiredAction`, `dueDate`, `knownRansomwareCampaignUse`）
を `Advisory` に写像する。KEV status は `references[].type = "kev"` と
`tags = ("kev", "known-exploited", ...)` で表現し、storage schema は変更しない。

## Vendor Advisory / RSS Adapter

目的:

- ベンダー固有のセキュリティ更新情報を取り込む。

初期方針:

- まず adapter interface と fixture を作る。
- 個別 vendor adapter は必要に応じて追加する。
- RSS/Atom は title / URL / published_at / summary を SourceRecord 化する。
- vendor advisory fixture は vendor advisory ID、CVE ID、severity、source URL を
  `Advisory.vendor_advisory_ids` / `Advisory.cve_ids` / `Advisory.references` に正規化する。
- RSS/feed fixture は live crawler ではなく、title / URL / summary / published_at /
  CVE ID を受け取る skeleton として扱う。

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

## Firecrawl Adapter (web_scrape)

目的:

- URL 指定で任意の Web ページを Markdown として取得し、Advisory に変換する。
- 構造化 API のない vendor advisory / blog 記事 / 公開セキュリティ情報に対応する。

SourceType: `"web_scrape"`

スキーママイグレーション: `db/migrations/*/0002_add_web_scrape_source_type.sql` にて `source_records.source_type` の CHECK 制約に `'web_scrape'` を追加済み。

実装: `src/spautopost/firecrawl_adapter.py`、依存: `firecrawl-py>=4.0`（`[spike]` extra）

設定項目:

| 環境変数 | 必須 | デフォルト | 説明 |
|----------|------|-----------|------|
| `FIRECRAWL_API_KEY` | ✅ 必須 | — | Firecrawl API key（`fc-...` 形式） |
| `FIRECRAWL_TIMEOUT_SECONDS` | 省略可 | 30 | スクレイプタイムアウト（秒） |
| `FIRECRAWL_MAX_CONTENT_CHARS` | 省略可 | 5000 | `summary` に使う Markdown の最大文字数 |

利用条件と制約:

- API key は [firecrawl.dev](https://firecrawl.dev) で取得する（Free プランは ~500 pages/月）
- スクレイピング対象サイトの利用規約を個別確認すること（オペレーター責任）
- robots.txt を遵守すること
- 構造化 API が存在するソース（NVD・JVN・CISA KEV）は公式 adapter を優先する
- CVE ID・severity の自動抽出は M2 以降（LLM 連携が必要）
- 取得コンテンツは Draft Composition と人間レビューを通じてサニタイズする

採否判断: ✅ M1 optional で採用（詳細は `docs/spikes/firecrawl-adapter-spike.md` を参照）

## Related Issues

- #7 Implement manual advisory input and validation
- #11 Implement NVD adapter
- #12 Implement MyJVN adapter
- #13 Define KEV and vendor advisory adapter interface
- #21 Add scheduler and external collector import boundary
- #34 Spike: Evaluate Firecrawl source adapter
