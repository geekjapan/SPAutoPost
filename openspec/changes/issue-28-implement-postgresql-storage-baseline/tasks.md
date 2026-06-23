## 1. 共有 contract suite（RED）

- [ ] 1.1 ストレージポート向けの共有 contract テスト suite を作成する（両 backend をパラメタライズ。get/list/upsert/append-only/create_if_absent/idempotency/タイムスタンプ往復を網羅）
- [ ] 1.2 contract suite が未実装状態で RED になることを確認する

## 2. DTO 定義

- [ ] 2.1 6 エンティティの frozen-dataclass DTO を定義する（spec 追加列を含む。`summary_for_users` / `impact` / `idempotency_key` は非 Optional）
- [ ] 2.2 `event_type` を 15 値の `Literal`、`status` / `publication_status` / `operation` 等の enum を型で表現する
- [ ] 2.3 全 timestamp を tz-aware UTC とし、naive datetime を境界で拒否する検査を入れる

## 3. port / errors 定義

- [ ] 3.1 repository Protocol（`migrate` / `transaction` / `close`、各 repo の `upsert` / `get(Optional)` / `list`、append-only、`create_if_absent` / `get_by_idempotency_key`）を定義する
- [ ] 3.2 `StorageError` 階層を定義する（制約違反 / ドリフト / 設定不整合 / 未知 provider）

## 4. SQLite baseline

- [ ] 4.1 `db/migrations/sqlite/0001_baseline.sql` を作成する（6 テーブル / CHECK / FK / UNIQUE index / TEXT・REAL 型 / 非トランザクション DDL 禁止のヘッダコメント）

## 5. migration ランナー + テスト

- [ ] 5.1 migration ランナーを実装する（`schema_migrations` ブートストラップ / 方言ディレクトリ選択 / 1 ファイル 1 トランザクション / 昇順適用 / SHA-256 ドリフト検知 / 再実行 no-op）
- [ ] 5.2 ランナーのユニットテスト（初回適用 / 再実行 no-op / チェックサム不一致で停止 / 失敗時ロールバックで ledger 不記録）を作成する

## 6. SQLite backend（GREEN）

- [ ] 6.1 SQLite backend を実装する（`PRAGMA foreign_keys=ON` / JSON=`json.dumps` TEXT / 正準 ISO-8601 UTC / 単一ライター逐次 create_if_absent）
- [ ] 6.2 共有 contract suite を SQLite で GREEN にする

## 7. PostgreSQL baseline

- [ ] 7.1 `db/migrations/postgres/0001_baseline.sql` を作成する（6 テーブル / CHECK（audit 15 値含む）/ FK / UNIQUE index / JSONB・timestamptz・numeric 型 / 非トランザクション DDL 禁止のヘッダコメント）

## 8. スキーマ等価テスト

- [ ] 8.1 PG / SQLite baseline 間の等価ユニットテスト（table / column / CHECK enum / FK / UNIQUE index 集合の diff）を作成する

## 9. PostgreSQL backend（CI 必須）

- [ ] 9.1 PostgreSQL backend を実装する（`ON CONFLICT` で race-safe な create_if_absent / JSONB・timestamptz の往復）
- [ ] 9.2 CI に Postgres service を追加し、共有 contract suite を PG と SQLite の両方で実行することを必須化する（人間ゲート対象）

## 10. factory

- [ ] 10.1 `StorageConfig` からの factory を実装する（アクティブ provider の必須フィールド assert / クロス provider フィールド顕在化 / psycopg 遅延 import / 未知 provider は防御的 `StorageError`）

## 11. psycopg optional extra + migrate CLI

- [ ] 11.1 `psycopg` を `pyproject.toml` の optional extra として追加し、postgres 分岐でのみ遅延 import する
- [ ] 11.2 migration ランナーを薄い CLI（例: `migrate` サブコマンド）として公開する

## 12. 検証

- [ ] 12.1 ローカルで ruff / mypy / pytest（カバレッジ 80%+）を通す
- [ ] 12.2 README / docs にストレージ・migration の利用方法を追記する（data-model.md の event_type reconcile note を含む）
- [ ] 12.3 `openspec validate issue-28-implement-postgresql-storage-baseline --strict` を通す
- [ ] 12.4 Issue #28 の受け入れ条件（正本 PG schema / migration baseline / ストレージポート / 6 repo / idempotency NOT NULL+UNIQUE / SQLite adapter）を満たすことを確認する
