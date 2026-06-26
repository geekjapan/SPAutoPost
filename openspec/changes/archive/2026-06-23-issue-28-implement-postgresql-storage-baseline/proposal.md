## Why

SPAutoPost の正本データ（SourceRecord / Advisory / DraftPost / ReviewEvent / Publication / AuditEvent）を永続化する基盤が無く、後続 Issue（#10 dry-run/audit、#19 review/approval、#20 publish idempotency）はいずれも「正本である PostgreSQL schema」「重複投稿を防ぐ idempotency 制約」「DB を差し替え可能なストレージ抽象」に依存する。`docs/decisions/2026-06-22-db-migration-strategy.md`（Accepted）は schema 正本を SQL migration とし `#28 で PostgreSQL schema と migration baseline を実装する` と明記しているため、まずこの土台を確定する。

本 change は Issue #28（M1: PostgreSQL storage baseline）に対応し、`docs/specs/data-model.md`・`docs/specs/audit-log.md`・`docs/specs/sharepoint-publishing.md`・`docs/decisions/2026-06-22-db-migration-strategy.md` を正本として、その方針を OpenSpec capability に落とし込む。既存の `src/spautopost/config.py`（`StorageConfig(provider/database_url/sqlite_path)`）と整合し、新規 config キーは追加しない。

## What Changes

- 正本 PostgreSQL schema を 6 エンティティ（`source_records` / `advisories` / `draft_posts` / `review_events` / `publications` / `audit_events`）について SQL で定義する。検証ゲートで確定した必須列・CHECK 制約・FK を含む。
- SQL ファーストの migration baseline（`db/migrations/{postgres,sqlite}/0001_baseline.sql`）と、stdlib + psycopg ベースの最小 migration ランナー（チェックサム込み ~120 行）を導入する。Alembic / Flyway / yoyo は不採用。
- ストレージポート（repository パターンの Python Protocol）を導入し、DB バックエンドを差し替え可能にする。frozen-dataclass DTO、Secret 非保持、tz-aware UTC timestamp、SQL/方言を呼び出し側へ露出しない。
- 6 エンティティ全てに repository（SourceRecord を含むフル実装）を提供する。
- `publications.idempotency_key` を **NOT NULL + UNIQUE** とし、重複投稿を DB 層で封鎖する（`create_if_absent` で race-safe な作成）。
- ローカル/テスト用の SQLite adapter を提供し、PostgreSQL と同一の共有 contract suite を両バックエンドで実行する。
- **CI 変更**: PostgreSQL を CI で必須化する（Postgres service を起動し、PG と SQLite の両方で共有 contract suite を実行する）。任意の `DATABASE_URL` ゲートにはしない。
- **非対象**: `idempotency_key` の **導出ロジック**（#20 所有。#28 は制約強制と null/空キー拒否のみ）、本番 DB 運用、down-migration、接続プール/timeout チューニング、高度な並行制御、本番監視。

## Capabilities

### New Capabilities

- `storage-port`: repository の Python Protocol、frozen-dataclass DTO、`StorageConfig` からのバックエンド選択（factory）。読み取り契約（`get()` は不在時 `Optional` を返し raise しない、list 系は `created_at ASC, PK ASC` の決定論的順序と limit/offset）、アクティブ provider の必須フィールド assert・クロス provider フィールドの顕在化・psycopg の遅延 import を定める。
- `storage-schema`: 6 エンティティテーブルの PostgreSQL / SQLite 両方言スキーマ。必須列・CHECK 制約（`audit_events.event_type` は audit-log.md の 15 値）・FK・方言別型マッピング（JSONB/timestamptz/numeric ↔ TEXT/REAL + 正準 ISO-8601 UTC / `json.dumps`）を定める。
- `storage-migration`: SQL ファーストの migration baseline と最小ランナー。`schema_migrations(version, checksum, applied_at)` のブートストラップ、1 ファイル 1 トランザクション、昇順適用、SHA-256 ドリフト検知、再実行 no-op、非トランザクション DDL 禁止、二重ファイルドリフトを防ぐスキーマ等価テストを定める。
- `storage-idempotency`: `publications.idempotency_key` の NOT NULL + UNIQUE 制約と `create_if_absent`（PG は `ON CONFLICT` で race-safe、SQLite は単一ライター逐次）。null/空キーの境界拒否を定める。導出ロジックは #20 に委譲する。

### Modified Capabilities

<!-- openspec/specs/ には storage 系 capability が存在しない（application-skeleton / configuration / secret-management のみ）。docs/specs/ は設計ノートであり OpenSpec spec ではないため、本 change は新規 capability のみ。 -->

## Impact

- **新規コード（実装フェーズ）**: `src/spautopost/storage/`（`port.py` / `models.py`（DTO）/ `factory.py` / `errors.py` / `migrate.py`（ランナー）/ SQLite backend / PostgreSQL backend）、`db/migrations/{postgres,sqlite}/0001_baseline.sql`、`tests/`（共有 contract suite・migration ランナーテスト・スキーマ等価テスト）。
- **依存関係**: `psycopg` を optional extra として `pyproject.toml` に追加し、postgres 分岐でのみ遅延 import する。SQLite は stdlib `sqlite3` で新規依存なし。SQL ランナーは stdlib + psycopg の自前最小実装。
- **CI**: GitHub Actions に Postgres service を追加し、共有 contract suite を PG と SQLite の両方で実行することを必須化する（人間ゲート対象）。
- **既存仕様との整合**: `StorageConfig(provider/database_url/sqlite_path)` をそのまま利用し、新規 config キーは追加しない。
- **正本との関係（要 follow-up）**: `audit_events.event_type` は **audit-log.md の 15 値** を採用する。`docs/specs/data-model.md` の 8 値はその subset であり、後続で data-model.md 側を 15 値の subset として整合（reconcile）させる必要がある（本 change で note を残す）。
- **非対象による制約**: `idempotency_key` 導出は #20、本番 DB 運用・down-migration・接続プールは #28 のスコープ外。
