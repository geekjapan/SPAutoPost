## Context

SPAutoPost は GitHub 駆動・仕様駆動で、core language は Python（`docs/decisions/2026-06-22-mvp-runtime-and-language.md`）。`docs/decisions/2026-06-22-db-migration-strategy.md`（Accepted）は「DB schema の正本は SQL migration」「M1 で `db/migrations` に baseline を置く」「local/test SQLite adapter は PostgreSQL schema と矛盾しない範囲で互換実装」「Admin UI/API と Python core は同じ migration version を前提に動作」と定めており、#28 はこれを実装する。

既存 `src/spautopost/config.py` は `StorageConfig(provider: postgresql|sqlite, database_url, sqlite_path)` を検証済みで提供する。本 change はこの config を入力とし、新規 config キーは追加しない。データモデルの正本は `docs/specs/data-model.md` / `docs/specs/audit-log.md` / `docs/specs/sharepoint-publishing.md`。本 change の depth は「正本 schema・migration baseline・ストレージ抽象・idempotency 制約の確定」であり、`idempotency_key` の導出ロジック・本番 DB 運用・接続プールは対象外。

## Goals / Non-Goals

**Goals:**
- 6 エンティティ（SourceRecord / Advisory / DraftPost / ReviewEvent / Publication / AuditEvent）の正本 PostgreSQL schema を SQL で定義する。
- SQL ファーストの migration baseline と最小 migration ランナー（チェックサム込み）を提供する。
- DB を差し替え可能にする repository パターンのストレージポートと、6 エンティティのフル repository を提供する。
- `publications.idempotency_key` の NOT NULL + UNIQUE で重複投稿を DB 層で封鎖する。
- ローカル/テスト用 SQLite adapter を提供し、PG と SQLite を共有 contract suite で検証する。CI で PG を必須化する。

**Non-Goals:**
- `idempotency_key` の **導出ロジック**（#20 所有）。#28 は制約強制 + null/空キー拒否のみ。
- 本番 DB 運用、down-migration、migration status UX、自動生成。
- 接続プール / timeout チューニング、高度な並行制御、本番監視。
- 認証・認可・Secret 投入・実 publish（人間ゲート対象）。

## Decisions

- **ストレージポート（repository パターン）**: ORM 非依存の Python Protocol。`port.py`（Protocol）/ `models.py`（frozen-dataclass DTO）/ `factory.py`（backend 選択）/ `errors.py`（`StorageError` 階層）/ `migrate.py`（ランナー）に分割。SQL・方言・ドライバを呼び出し側へ露出しない。理由: DB 差し替え（SQLite ↔ PostgreSQL）とテスト容易性。代替（ORM 直結）は migration-strategy の「ORM に依存しすぎない」方針に反する。

- **SQL ファースト + 自前最小ランナー（Alembic/Flyway/yoyo 不採用）**: stdlib + psycopg の自前ランナー（チェックサム込み ~120 行）。Alembic は ORM 結合が強く migration-strategy の方針に反する。Flyway は JVM 依存で Python core に過剰。yoyo は新規依存追加で「依存最小」に反する。自前なら 1 ファイル 1 トランザクション・SHA-256 ドリフト検知・再実行 no-op を完全制御できる。

- **二方言 baseline（PostgreSQL 正本 / SQLite 互換）**: `db/migrations/{postgres,sqlite}/0001_baseline.sql`。PG=JSONB/timestamptz/numeric、SQLite=TEXT/REAL + 正準 ISO-8601 UTC + `json.dumps`。二重ファイルのドリフトはスキーマ等価ユニットテスト（table/column/CHECK enum/FK/UNIQUE index 集合の diff）で構造的にガード。代替（単一マニフェストからの SQL 生成）は YAGNI で延期し、等価テストで代替する。

- **AuditEvent event_type = audit-log.md の 15 値**: `source_fetch` / `source_parse` / `normalize` / `triage` / `draft_generate` / `draft_validate` / `review` / `approve` / `reject` / `regenerate` / `publish_dry_run` / `publish_create` / `publish_update` / `publish_result` / `error`。data-model.md は 8 値で記載しているが、audit-log.md がより詳細で監査要件の正本。data-model.md の 8 値は 15 値の subset として後続で reconcile する（Open Questions 参照）。

- **SourceRecord をフル実装で含める（6 番目のエンティティ）**: schema だけでなく repository も含める。理由: Advisory の source_refs 追跡・条件付き GET キャッシュ（`http_status`/`etag`/`last_modified`）の永続化が後続の収集系で必要。schema-only への縮退は issue owner 確認事項だったが、フル実装で確定。

- **PostgreSQL を CI で必須化**: CI で Postgres service を起動し、共有 contract suite を PG と SQLite の両方で実行する。任意の `DATABASE_URL` ゲートにはしない。理由: 正本である PG が CI 未検証だと「SQLite は pass / PG は fail」のドリフトを見逃す。

- **idempotency: NOT NULL + UNIQUE + create_if_absent**: NOT NULL で PG の複数 NULL すり抜けを封鎖。PG は `ON CONFLICT` で race-safe、SQLite は単一ライター逐次。`create_if_absent -> (pub, created)` と `get_by_idempotency_key` を提供。導出は #20。

- **ランタイムスタイル**: frozen-dataclass DTO、Secret 非保持、全 timestamp tz-aware UTC（naive は境界で `StorageError`）、正準フォーマット `isoformat(timespec='seconds')`。psycopg は optional extra（postgres 分岐で遅延 import）、SQLite は stdlib `sqlite3` で新規依存なし。

## Risks / Trade-offs

- [二方言間の semantic ドリフト] → 共有 contract suite を両 backend で実行 + PG 必須 CI + スキーマ等価テストで三重に緩和。
- [二重ファイルドリフト] → スキーマ等価ユニットテストで構造ガード。
- [down-migration が無い] → M1 PoC では前進専用を許容（本番 DB 運用は #28 非対象）。
- [psycopg 依存] → optional extra + 遅延 import。SQLite 経路は psycopg 不在でも動作。
- [idempotency_key 導出が #20 所有] → #28 は NOT NULL + UNIQUE で先行防御し、導出は #20 に委譲。
- [SQLite の単一ライター] → 並行 race は SQLite で非対応（ローカル/テスト用途のため許容）。PG は ON CONFLICT で race-safe。
- [JSON 列の不透明性] → クエリ必須列（published_at/updated_at、監査の target_site_id 等）のみ top-level 化し、それ以外は JSON に格納。
- [config のクロス provider フィールド未検証] → `_validate_storage` の厳格化は follow-up とし、本 change では factory 側で顕在化（assert / 警告 / エラー）。
- [未知 provider パス] → factory で防御的に `StorageError`（通常 config validation で到達しないが防御用）。
- [接続プール/timeout 未対応] → 単一接続のみ（本番運用は対象外）。

## Migration Plan

新規追加のみ（既存ストレージ実装は無い）。導入手順は tasks.md の TDD 順に従う: 共有 contract suite（RED）→ DTO → port/errors → sqlite baseline → ランナー + テスト → sqlite backend（GREEN）→ postgres baseline → スキーマ等価テスト → postgres backend（CI 必須）→ factory → psycopg optional extra + migrate CLI → ruff/mypy/pytest（≥80%）+ docs。ロールバックはコミット revert で完結（前進専用 migration のため DB 側 down は無し）。

## Open Questions

- `idempotency_key` の導出ロジック（`draft_id + target_site_id + target_page_library_id` をベースに `advisory_ids` を含めるか）は #20 の OPEN DECISION。本 change のスキーマ列変更は不要（制約のみ先行）。
- `docs/specs/data-model.md`（AuditEvent event_type 8 値）と `docs/specs/audit-log.md`（15 値）の reconcile。本 change は 15 値を採用し、data-model.md 側を 15 値の subset として後続で整合させる必要がある（docs 更新の follow-up）。
- config `_validate_storage` のクロス provider フィールド厳格化を config 側に寄せるか（本 change は factory 側で顕在化）。
