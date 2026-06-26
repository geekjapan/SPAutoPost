## Why

Issue #21 では、manual run と scheduled run を責務で分離し、外部 collector から normalized advisory を受け取るための import 境界を定義・実装する必要がある。現在は `job_entrypoint.py` が実行方式を区別していないため、将来的な crawler/collector の分離に伴い変更コストが増える。また、外部データを信頼境界なしに取り込むことはセキュリティ上の危険を持つ。

## What Changes

- manual run と scheduled run の RunMode を定義し、`job_entrypoint.py` でタグ付けする。
- 差分収集の基点となる `CollectionCheckpoint` をファイルベースで管理する軽量な仕組みを追加する。
- external collector からの file import 境界を定義し、schema ベースの入力検証を必須にする（fail fast, 不正データは取り込まない）。
- import schema を `docs/specs/external-collector-boundary.md` に明記する（既存 spec の import schema 節を実装例つきで整合）。
- 失敗時の retry/backoff 最小実装（指数バックオフ）を共通ユーティリティとして追加する。
- API import / queue boundary は YAGNI（本 Issue では Port/adapter として定義のみ、実装は後続 Issue）。
- 将来 crawler/collector を別プログラムへ分離しても SPAutoPost 本体の変更が最小で済む Port abstraction を維持する。

## Capabilities

### New Capabilities

- `scheduler-run-mode`: manual/scheduled 実行方式を表す RunMode と、job_entrypoint への組み込み。
- `collection-checkpoint`: 差分収集のチェックポイント（最終収集時刻）を保持する軽量ストア。
- `external-collector-import`: 外部 collector から normalized advisory を file import する境界（schema 検証必須）。
- `retry-backoff`: 失敗時の指数バックオフ付き retry ユーティリティ。

### Modified Capabilities

- `job-entrypoint`: RunMode タグを追加し、manual/scheduled の識別を明示する。

## Impact

- `src/spautopost/scheduler.py`（新規）
- `src/spautopost/collection_checkpoint.py`（新規）
- `src/spautopost/external_collector_import.py`（新規）
- `src/spautopost/retry.py`（新規）
- `src/spautopost/job_entrypoint.py`（RunMode タグ追加）
- `src/spautopost/cli.py`（`import-external` コマンド追加）
- `docs/specs/external-collector-boundary.md`（import schema を実装例つきで整合）
- `tests/`（新規テスト）
- `openspec/changes/issue-21-add-scheduler-external-collector-boundary/`
