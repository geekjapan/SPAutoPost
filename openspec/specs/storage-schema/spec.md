# storage-schema Specification

## Purpose
TBD - created by archiving change issue-28-implement-postgresql-storage-baseline. Update Purpose after archive.
## Requirements
### Requirement: 6 エンティティの正本テーブル

システムは 6 エンティティのテーブル `source_records` / `advisories` / `draft_posts` / `review_events` / `publications` / `audit_events` を PostgreSQL（正本）と SQLite の両方言で定義しなければならない（SHALL）。両方言のスキーマは同一のテーブル集合・列集合・CHECK enum・FK・UNIQUE index を表現しなければならない（SHALL）。

#### Scenario: 全テーブルが作成される
- **WHEN** baseline migration を適用する
- **THEN** PostgreSQL でも SQLite でも 6 テーブルが作成される

#### Scenario: SourceRecord をルートエンティティとして含む
- **WHEN** スキーマを検査する
- **THEN** `source_records` テーブルが存在し、`http_status` / `etag` / `last_modified`（条件付き GET キャッシュ用）の列を持つ

### Requirement: DraftPost の必須列

システムは `draft_posts.summary_for_users` と `draft_posts.impact` を NOT NULL 列として定義しなければならない（SHALL）。`draft_posts.deadline` 列を持ち（任意）、`draft_posts.status` は data-model.md の DraftStatus enum 全値を許容する CHECK 制約を持たなければならない（SHALL）。

#### Scenario: summary_for_users と impact は NOT NULL
- **WHEN** `summary_for_users` または `impact` を NULL とする DraftPost を挿入しようとする
- **THEN** NOT NULL 制約違反となり、`StorageError` を送出する

#### Scenario: status は DraftStatus enum で制約される
- **WHEN** DraftStatus enum 外の status 値を挿入しようとする
- **THEN** CHECK 制約違反となり拒否される

### Requirement: Advisory の時系列列と JSON 列

システムは `advisories.published_at` と `advisories.updated_at` を top-level 列として定義し（時系列クエリ用）、`vendor_advisory_ids` を JSON 列に格納しなければならない（SHALL）。`cvss_score` は数値型（PostgreSQL: numeric、SQLite: REAL）で表現しなければならない（SHALL）。

#### Scenario: 時系列列が top-level に存在する
- **WHEN** `advisories` スキーマを検査する
- **THEN** `published_at` と `updated_at` が独立した列として存在する

#### Scenario: vendor_advisory_ids を JSON として往復する
- **WHEN** `vendor_advisory_ids` を含む Advisory を upsert して再取得する
- **THEN** 配列値が JSON シリアライズ/デシリアライズを経て同一内容で復元される

### Requirement: Publication の投稿先・操作列

システムは `publications` に `operation`（dry-run / create / update / publish）、`published_at`、`target_list_id`、`target_page_library_id`、`sharepoint_page_id` を sharepoint-publishing.md / data-model.md の名称で定義しなければならない（SHALL）。曖昧な汎用 `page_id` 列は使用してはならない（SHALL NOT）。`publication_status` は data-model.md の enum を CHECK 制約で強制しなければならない（SHALL）。

#### Scenario: 投稿先列が spec 名称で存在する
- **WHEN** `publications` スキーマを検査する
- **THEN** `operation` / `published_at` / `target_list_id` / `target_page_library_id` / `sharepoint_page_id` 列が存在し、汎用 `page_id` 列は存在しない

#### Scenario: publication_status を enum で制約する
- **WHEN** data-model.md の enum 外の `publication_status` を挿入しようとする
- **THEN** CHECK 制約違反となり拒否される

### Requirement: AuditEvent の event_type 15 値と監査必須列

システムは `audit_events.event_type` を audit-log.md の 15 値（`source_fetch` / `source_parse` / `normalize` / `triage` / `draft_generate` / `draft_validate` / `review` / `approve` / `reject` / `regenerate` / `publish_dry_run` / `publish_create` / `publish_update` / `publish_result` / `error`）に限定する CHECK 制約で定義しなければならない（SHALL）。システムは監査クエリ用に `target_site_id` / `idempotency_key` / `operation` / `provider_name` / `prompt_version` / `error_code` / `error_message` を top-level 列として定義しなければならない（SHALL）。

注記: `docs/specs/data-model.md` は AuditEvent の event_type を 8 値で記載しているが、本 change は audit-log.md の 15 値を正本として採用する。data-model.md の 8 値は 15 値の subset として後続で整合（reconcile）させる必要がある。

#### Scenario: 15 値の event_type を受理する
- **WHEN** 15 値のいずれかを `event_type` とする AuditEvent を挿入する
- **THEN** CHECK 制約を満たし永続化される

#### Scenario: enum 外の event_type を拒否する
- **WHEN** 15 値に含まれない `event_type` を挿入しようとする
- **THEN** CHECK 制約違反となり拒否される

#### Scenario: 監査必須列が top-level に存在する
- **WHEN** `audit_events` スキーマを検査する
- **THEN** `target_site_id` / `idempotency_key` / `operation` / `provider_name` / `prompt_version` / `error_code` / `error_message` 列が存在する

### Requirement: 外部キーによる関連の強制

システムはエンティティ関連（SourceRecord → Advisory → DraftPost → ReviewEvent / Publication → AuditEvent）を外部キーで強制しなければならない（SHALL）。SQLite では `PRAGMA foreign_keys=ON` を有効にしなければならない（SHALL）。

#### Scenario: FK 違反を拒否する
- **WHEN** 存在しない親レコードを参照する子レコードを挿入しようとする
- **THEN** FK 制約違反となり拒否される

#### Scenario: SQLite で FK が有効である
- **WHEN** SQLite backend で接続を確立する
- **THEN** `PRAGMA foreign_keys=ON` が設定され FK が強制される

### Requirement: PostgreSQL と SQLite の型マッピング

システムは方言間で正準な型マッピングを定義しなければならない（SHALL）。PostgreSQL は JSONB / timestamptz / numeric を用い、SQLite は TEXT / REAL を用いる。SQLite では JSON を `json.dumps` の TEXT として格納し、timestamp は正準 ISO-8601 UTC 文字列（`isoformat(timespec='seconds')`、例 `2024-01-01T00:00:00+00:00`）として格納しなければならない（SHALL）。

#### Scenario: 方言別の型が適用される
- **WHEN** PostgreSQL と SQLite それぞれの baseline を適用する
- **THEN** PostgreSQL は JSONB/timestamptz/numeric、SQLite は TEXT/REAL の対応列を持つ

#### Scenario: SQLite の timestamp が正準フォーマットで格納される
- **WHEN** tz-aware UTC datetime を SQLite に保存する
- **THEN** `2024-01-01T00:00:00+00:00` 形式の ISO-8601 UTC 文字列として格納され、往復で同一値に復元される

