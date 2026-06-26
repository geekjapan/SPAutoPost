# External Collector Boundary Specification

## Status

Implemented (Issue #21)

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

### エンベロープ（必須）

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `schema_version` | string | MUST | 現在は `"1.0"` |
| `producer` | string | MUST | collector の識別子（例: `"my-collector-v1"`） |
| `generated_at` | string | MUST | ISO-8601 UTC 日時（例: `"2026-01-01T00:00:00Z"`） |
| `correlation_id` | string | optional | トレース用 ID |
| `advisories` | array | MUST | advisory オブジェクトの配列 |

### advisory オブジェクト（各要素）

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `title` | string | MUST | 空文字不可 |
| `summary` | string | optional | 省略時は title を使用 |
| `advisory_id` | string | optional | 省略時は自動生成 |
| `severity` | string | optional | `critical` / `high` / `medium` / `low` / `unknown` |
| `cve_ids` | string[] | optional | `CVE-YYYY-NNNNN` 形式 |
| `jvn_ids` | string[] | optional | `JVNDB-YYYY-NNNNNN` / `JVN#NNNNNNNN` 形式 |
| `vendor_advisory_ids` | string[] | optional | ベンダー固有 ID |
| `references` | array | MUST | 1 件以上必要 |
| `references[].label` | string | MUST | 参照先の表示名 |
| `references[].url` | string | MUST | http(s) URL |
| `references[].type` | string | optional | `vendor` / `advisory` / `other` 等 |

### 最小 JSON 例

```json
{
  "schema_version": "1.0",
  "producer": "my-collector-v1",
  "generated_at": "2026-06-01T00:00:00Z",
  "correlation_id": "abc-123",
  "advisories": [
    {
      "advisory_id": "MY-2026-0001",
      "title": "Example Product の重大な脆弱性",
      "summary": "Example Product v1.x に認証バイパスの脆弱性が発見されました。",
      "severity": "critical",
      "cve_ids": ["CVE-2026-0001"],
      "references": [
        {
          "label": "Vendor Advisory",
          "url": "https://example.com/security/2026-0001",
          "type": "vendor"
        }
      ]
    }
  ]
}
```

## Validation

import 時に検査する項目:

- `schema_version`, `producer`, `generated_at` の存在
- `advisories` が配列である
- 各 advisory の `title` が非空文字列
- 各 advisory の `references` が 1 件以上
- `references[].url` が http(s) URL
- `severity` が許可値 (`critical` / `high` / `medium` / `low` / `unknown`)
- `cve_ids` が `CVE-YYYY-NNNNN` 形式
- `jvn_ids` が `JVNDB-YYYY-NNNNNN` / `JVN#NNNNNNNN` / `JVNVU#NNNNNNNN` 形式

**動作方針**: エンベロープ検証が失敗した場合はファイル全体を reject する。
advisory レコード単位の検証が失敗した場合は当該レコードを reject し（`rejected_count` に計上）、
他の有効なレコードは取り込む。全体処理は止めない。

## Scheduler と RunMode

`src/spautopost/scheduler.py` で定義する `RunMode` で manual / scheduled 実行を区別する。

| RunMode | 対象ジョブ |
|---|---|
| `"manual"` | `dry-run`, `publish-approved` |
| `"scheduled"` | `collect`, `generate`, その他 |

`job_entrypoint.run_job()` は `JobContext(job_name, run_mode)` を生成し、
将来の audit log 連携に使用できる。

## 差分収集 (Collection Checkpoint)

`src/spautopost/collection_checkpoint.py` の `CollectionCheckpointStore` が
最終収集時刻を JSON ファイルに保存する。

- 初回実行時はチェックポイントがなく `None` を返す（エラーにしない）。
- 収集後に `save()` で更新する。
- **並行実行・分散環境では競合する**（単一プロセス前提）。
  複数インスタンスが必要になった時点で StoragePort ベースの実装へ移行する。

## Retry / Backoff

`src/spautopost/retry.py` の `with_retry(fn, config)` で指数バックオフ付きの再試行を提供する。

```python
from spautopost.retry import RetryConfig, with_retry

config = RetryConfig(max_attempts=3, base_delay_seconds=1.0, max_delay_seconds=60.0)
result = with_retry(lambda: fetch_from_api(), config)
```

- 全試行が失敗した場合は最後の例外を再発生させる。
- `sleep_fn` を差し替えることでテスト可能。
- Retry-After ヘッダ解析・サーキットブレーカーは後続 Issue。

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
