## ADDED Requirements

### Requirement: SQL ファーストの migration baseline

システムは migration baseline を方言別の SQL ファイル `db/migrations/postgres/0001_baseline.sql` と `db/migrations/sqlite/0001_baseline.sql` として提供しなければならない（SHALL）。ランナーは対象 backend の provider に応じて方言ディレクトリを選択しなければならない（SHALL）。schema 正本は SQL migration であり、ORM 由来の自動生成に依存してはならない（SHALL NOT）。

#### Scenario: 方言ディレクトリを選択する
- **WHEN** `provider=postgresql` のバックエンドで migration を適用する
- **THEN** `db/migrations/postgres/` 配下のファイルのみを適用し、SQLite では `db/migrations/sqlite/` 配下のみを適用する

### Requirement: schema_migrations のブートストラップと ledger 記録

ランナーは `schema_migrations(version, checksum, applied_at)` テーブルを `CREATE TABLE IF NOT EXISTS` で冪等にブートストラップしなければならない（SHALL）。このブートストラップは番号付き migration ファイルの外で行わなければならない（SHALL）。各 migration ファイルは `version` と `checksum` を ledger に記録しなければならない（SHALL）。

#### Scenario: 初回適用で ledger を作る
- **WHEN** 空の DB に対して migration を実行する
- **THEN** `schema_migrations` が作成され、適用した各ファイルの version と checksum が記録される

### Requirement: 1 ファイル 1 トランザクションで昇順適用する

ランナーは migration ファイルを version 昇順で適用し（SHALL）、ファイルごとに BEGIN → SQL 適用 → ledger INSERT → COMMIT を 1 トランザクションで実行しなければならない（SHALL）。適用に失敗した場合はそのトランザクションをロールバックし、ledger に当該 version を記録してはならない（SHALL NOT）。migration ファイルに非トランザクション DDL（`CREATE INDEX CONCURRENTLY` 等）を含めてはならず（SHALL NOT）、その旨を migration ファイルのヘッダコメントで明示しなければならない（SHALL）。

#### Scenario: 昇順で適用する
- **WHEN** 複数 migration ファイルが存在する状態でランナーを実行する
- **THEN** version 昇順で適用される

#### Scenario: 失敗時にロールバックし ledger に残さない
- **WHEN** あるファイルの適用中に SQL エラーが発生する
- **THEN** そのトランザクションがロールバックされ、当該 version は `schema_migrations` に記録されない

### Requirement: 再実行は no-op、チェックサムドリフトで停止する

ランナーは既に適用済みの migration を再適用してはならない（SHALL NOT、再実行は no-op）。ランナーは適用済みファイルの内容から SHA-256 を再計算し、ledger 記録と不一致（ドリフト）を検知した場合は適用を停止して `StorageError` を送出しなければならない（SHALL）。

#### Scenario: 再実行が no-op になる
- **WHEN** 全 migration を適用済みの DB に対して再度ランナーを実行する
- **THEN** 何も適用せず正常終了する

#### Scenario: チェックサム不一致で停止する
- **WHEN** 適用済み migration ファイルの内容が改変され、SHA-256 が ledger と一致しない状態でランナーを実行する
- **THEN** 適用を行わず `StorageError` を送出する

### Requirement: 二重ファイルドリフトのスキーマ等価ガード

システムは PostgreSQL と SQLite の baseline 間のドリフトを防ぐスキーマ等価ユニットテストを提供しなければならない（SHALL）。テストは両方言のテーブル集合・列集合・CHECK enum 集合・FK 集合・UNIQUE index 集合を比較し、構造的差異を検出した場合は失敗しなければならない（SHALL）。

#### Scenario: 構造差異を検出する
- **WHEN** 一方の方言 baseline にのみ列や CHECK enum を追加する
- **THEN** スキーマ等価テストが差分を検出して失敗する
