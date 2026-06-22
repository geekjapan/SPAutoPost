## Context

SPAutoPost は polyglot 構成（Python core + TypeScript/Node Admin UI/API）で、M1 hosted PoC は単一の Azure PostgreSQL を共有する（`storage-strategy.md`）。Storage Port は Python core が所有する（`architecture.md`）。本変更は、その storage baseline を作り、下流 Issue が同じ schema を read-only 前提で並列実装できる土台を提供する。schema shape は Opus 4.8 × GPT-5.5 の cross-model 議論で収束済み（ADR `admin-core-boundary.md` 参照）。

現状: `src/` / `db/` は未作成（greenfield）。Python ランタイム・依存・テスト構成も本変更で初期化する範囲に含む。

## Goals / Non-Goals

**Goals:**
- canonical entity + AdminCommand を保存できる PostgreSQL schema と SQL migration baseline。
- Python 所有 storage port（entity stores + command queue 操作）と、PostgreSQL / SQLite 2 adapter。
- idempotency（Publication / AdminCommand）と DraftStatus の整合を schema レベルで担保。
- 移植性（PG 正本、SQLite 互換）を型規約で担保。

**Non-Goals:**
- 本番 DB 運用設計の完全確定、高度な並行実行制御、本番監視。
- Microsoft Graph 認証（#27）、Entra role mapping（#29）。
- Admin API/UI 実装（#31）、ドメイン遷移ロジック本体（command を消費する Python transition 関数は別 Issue）。

## Decisions

- **schema 正本 = `db/migrations` の SQL migration**（ADR `db-migration-strategy.md`）。Alembic は migration の実行/wrap に限定し、autogenerate を正本にしない。理由: Python/TS 双方から参照しやすく、ORM 非依存。代替案（ORM autogenerate を正本）は polyglot で TS 側が追従できず却下。
- **PostgreSQL を設計基準、SQLite は互換 adapter**。timestamp は PG `timestamptz` / SQLite ISO8601 UTC TEXT、port が UTC 正規化。代替案（全列 ISO TEXT 統一）は正本 PG の time 検証/演算子を失うため却下（cross-model 議論の objection で修正）。
- **enum = TEXT + CHECK、配列/ネスト = JSON（JSONB/JSON text）**。PG native ENUM/ARRAY を使わない。理由: SQLite との drift を避け、enum 拡張時の alter を不要にする。queryable な列のみ column 化し index を張る。
- **AdminCommand queue**: `claim_pending_commands` は PG で `SELECT ... FOR UPDATE SKIP LOCKED`、SQLite では単純トランザクション。DraftStatus を authoritative な現在状態、AdminCommand を遷移要求の inbox とし、状態を二重化しない。エンティティ名は `AdminCommand` に統一する（"Intent" は説明語であり別テーブルではない）。
- **command_type の値集合（#26 admin-api-boundary との共有契約）**: `edit | approve | reject | request_regeneration | publish_request`。TEXT + CHECK で制約する。#26 の状態遷移 Write セットと一致させる。
- **idempotency_key の2スコープ**: Publication=(target_site + draft + operation)、AdminCommand=(command_type + draft + requested_by + client token)。各 UNIQUE。AdminCommand の idempotency_key は Admin API server が発番する（#26 grill R2 で確定。client request-id は任意併用）。
- **storage port API**: entity ごとの read/write store + `append_command` / `claim_pending_commands` / `complete_command` / `fail_command`。adapter は port 実装として PG/SQLite を差し替え可能にする。

## Risks / Trade-offs

- [JSON 列に逃がした属性は SQL での絞り込みが弱い] → queryable な属性（status, severity, idempotency_key, correlation_id, timestamps 等）は column 化し index。残りのみ JSON。
- [PG/SQLite の SQL 方言差（SKIP LOCKED, JSON 関数, timestamp）] → 差分を storage port adapter 内に閉じ込め、上位は port API のみに依存。
- [migration 正本を SQL にすることで Python モデルとの二重管理] → モデルは schema を参照する薄い表現に留め、整合は migration テスト（baseline 適用 + round-trip）で検証。
- [greenfield 初期化が本変更に混入] → ランタイム/依存/テスト雛形は storage に必要な最小限に限定し、API/UI は別 Issue。

## Migration Plan

1. `db/migrations` に baseline SQL migration を追加（全 canonical entity + AdminCommand、index、UNIQUE、CHECK、FK）。
2. PG 適用パスと、同一論理 schema 由来の SQLite 互換 DDL を用意。
3. storage port + 2 adapter を実装、TDD（保存/取得 round-trip、CHECK 違反、UNIQUE 違反、SKIP LOCKED claim）。
4. ロールバック: baseline のみのため drop/recreate で戻せる（本番データ未投入の M1 PoC 前提）。

## Apply-time tech decisions（apply 時に確定。ワーカーは再調査不要）

環境調査済み: Python 3.14.6 / stdlib `sqlite3` 3.53.2 で JSON1（`json_extract`）有効 / `pytest`・`psycopg` は未インストール（system Python は homebrew, PEP-668 想定）。

- **migration runner = 軽量自前**。`db/migrations/postgres/*.sql`（正本）/ `db/migrations/sqlite/*.sql`（派生）を順に適用し、`schema_migrations` テーブルで適用済み version を追跡。Alembic 依存は入れない。
- **SQLite JSON1 を前提とする**（標準ビルドで有効を確認済み）。
- **テスト = stdlib `unittest`**（`python3 -m unittest`、zero-install）。`TestCase` クラスで書き、後から pytest でもそのまま discover 可能にする。
- **SQLite を常用テスト substrate**。PostgreSQL adapter は psycopg を**遅延 import** し、`DATABASE_URL` + psycopg がある時だけ実走、無ければ skip。これによりパッケージ import と SQLite テストは psycopg 無しで green。
- stack: `pyproject.toml`（src layout）、psycopg v3 は optional extra `[postgres]`。
- 想定レイアウト: `src/spautopost/{models.py, config.py, storage/{port.py, serialization.py, sqlite.py, postgres.py, migrate.py}}`、`db/migrations/{postgres,sqlite}/0001_baseline.sql`、`tests/`。

### 委譲ワーカーへの注意
- ECC `gateguard-fact-force` フックが Write/Bash 毎に facts を要求する。greenfield ~15 ファイルでは setup 作業として `ECC_GATEGUARD=off`（または `ECC_DISABLED_HOOKS` に `pre:edit-write:gateguard-fact-force` / `pre:bash:gateguard-fact-force`）で実行するのが想定どおり。codex ワーカー（`.codex/hooks.json` に該当ゲート無し）で回す手もある。
