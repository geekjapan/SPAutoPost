## Context

Issue #21 は M5 の一環として、既存 `job_entrypoint.py` を基点に manual/scheduled 実行方式を分離し、外部 collector からの normalized advisory を安全に取り込む境界を定義・実装する。

既存資産:
- `job_entrypoint.py`: `JOB_COMMANDS` マップで job 名 → CLI argv を解決。manual と scheduled の区別なし。
- `source_adapters.py`: `SourceAdapter` Protocol。fetch/normalize 責務が分離済み。
- `storage/models.py`: `SourceType` に `"external_collector"` が既に定義済み。
- `docs/specs/external-collector-boundary.md`: import schema の草案あり（本 change で実装と整合）。

## Goals / Non-Goals

**Goals:**

- manual run と scheduled run の RunMode を型として明示し、job_entrypoint から伝播させる。
- 差分収集のチェックポイント（最終収集時刻）を保持する最小の仕組みを追加する。
- external collector からの file import 境界（schema 検証 → Advisory 変換 → storage 保存）を実装する。
- 失敗時の retry/backoff（指数バックオフ）を共通ユーティリティとして提供する。
- API import / queue は Port 定義のみ（実装は後続 Issue）。
- 入力検証は必ず import 境界で行い、不正データは fail fast で reject する。

**Non-Goals:**

- 外部 collector 本体の実装。
- queue / topic / event-driven import の実装。
- 高可用ジョブ基盤（cron デーモン、Celery 等）。
- SharePoint publish の変更。
- 認証・認可・Secret 操作。

## Decisions

### 1. RunMode は Literal 型と dataclass で最小表現

`RunMode = Literal["manual", "scheduled"]` を定義し、`JobContext` dataclass に持たせる。`job_entrypoint.run_job()` は `JobContext` を受け取り、audit log に RunMode を付与できるようにする。現状の `JOB_COMMANDS` マップは変更しない（互換性保持）。

### 2. CollectionCheckpoint はファイルベースの JSON、StoragePort 不使用

差分収集の基点となる最終収集時刻を `CollectionCheckpoint` dataclass で表す。永続化は単一 JSON ファイルに直書きする（StoragePort を使わない）。将来 DB 管理が必要になった時点で Storage 側へ移行可能。

### 3. External collector import は Port + file import 実装の 2 層構造

`ExternalCollectorImportPort` Protocol を定義し、file import を実装する。
import 境界では schema_version / producer / generated_at / advisories を必須チェックし、不正フィールドを reject する。
`external_collector` SourceType（既存）を使い、`SourceRecord` と `Advisory` を生成して StoragePort へ保存する。

### 4. Retry/backoff は指数バックオフ付きの汎用関数

`RetryConfig(max_attempts, base_delay_seconds, max_delay_seconds, backoff_factor)` と `with_retry(fn, config)` を提供する。呼び出し元は callable を渡すだけでよい。実際の sleep は `time.sleep` を依存注入可能にして、テストでモック置換できる形にする。

### 5. import schema は docs/specs/external-collector-boundary.md と整合

既存草案にある最小 schema を実装に合わせて確定させる（schema_version, producer, generated_at, advisories）。ただし import 後は必ず SPAutoPost の Advisory → DraftPost → Review flow を通す。インポートしたテキストをそのまま SharePoint に出力することは許容しない。

## Risks / Trade-offs

- `CollectionCheckpoint` のファイルベース実装は並行実行・分散環境では競合する。本 Issue では単一プロセス前提。複数インスタンスが必要になった時点で DB 管理へ移行する。
- Retry はシンプルな指数バックオフのみ。レート制限ヘッダ（Retry-After）の解析は後続 Issue で対応。
- API import / queue は Port 定義のみで実装なし。将来の実装者が `ExternalCollectorImportPort` を実装すれば SPAutoPost 本体は変更不要。
