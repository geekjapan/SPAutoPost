## ADDED Requirements

### Requirement: Canonical entity の永続化

storage capability は `data-model.md` の canonical entity（SourceRecord, Advisory, DraftPost, ReviewEvent, Publication, AuditEvent）を保存・取得できなければならない（SHALL）。各 entity は実装言語に依存しない文字列 ID を持つ。

#### Scenario: DraftPost の保存と取得
- **WHEN** 有効な DraftPost（draft_id, advisory_ids, title, status 等）を storage port で保存する
- **THEN** 同じ draft_id で取得した DraftPost が保存内容と一致する

#### Scenario: DraftStatus が permitted な値に限定される
- **WHEN** DraftStatus 列に enum 外の値（例 `"done"`）を保存しようとする
- **THEN** CHECK 制約違反として拒否される

### Requirement: AdminCommand queue の永続化と claim

storage capability は AdminCommand/Intent 行を append し、Python worker が pending command を排他的に claim・完了/失敗できなければならない（SHALL）。これは Admin↔Python core 非同期境界（ADR `admin-core-boundary.md`）を支える。

#### Scenario: pending command の排他 claim
- **WHEN** 2つの worker が同時に `claim_pending_commands` を呼ぶ
- **THEN** 同一 command は1つの worker にのみ割り当てられる（PostgreSQL は SKIP LOCKED）

#### Scenario: command の完了記録
- **WHEN** claim 済み command に対し `complete_command` を呼ぶ
- **THEN** status が `succeeded` になり processed_at が記録される

### Requirement: idempotency_key による重複検知

storage capability は Publication と AdminCommand の idempotency_key に対しそれぞれ UNIQUE 制約を持たなければならない（SHALL）。スコープは互いに独立する。

#### Scenario: 重複 Publication の拒否
- **WHEN** 既存と同じ idempotency_key を持つ Publication を挿入する
- **THEN** UNIQUE 制約違反として重複が検知される

### Requirement: PostgreSQL を正本とする SQL migration baseline

schema の正本は `db/migrations` 配下の SQL migration でなければならない（SHALL, ADR `db-migration-strategy.md`）。ORM の autogenerate を schema 正本にしてはならない（MUST NOT）。

#### Scenario: migration baseline の適用
- **WHEN** 空の PostgreSQL に migration baseline を適用する
- **THEN** 全 canonical entity と AdminCommand のテーブル・index・制約が作成される

### Requirement: SQLite 互換 adapter

storage capability は local/test 用に、PostgreSQL 正本 schema と矛盾しない SQLite adapter を提供しなければならない（SHALL）。同一論理 schema から派生させる。

#### Scenario: 同一 port API での SQLite 動作
- **WHEN** SQLite adapter を使って DraftPost を保存・取得する
- **THEN** PostgreSQL adapter と同じ storage port API で同じ結果が得られる

### Requirement: 型・ポータビリティ規約

storage capability は移植性のため、enum 類を TEXT + CHECK 制約で表現し（PostgreSQL native ENUM/ARRAY を使わない、MUST NOT）、配列・ネスト構造を JSON（PostgreSQL JSONB / SQLite JSON text）として port の背後に保持しなければならない（SHALL）。timestamp は PostgreSQL `timestamptz` / SQLite ISO8601 UTC TEXT とし、port が UTC へ正規化する。

#### Scenario: ネスト構造の round-trip
- **WHEN** references / affected_products / validation_warnings を含む entity を保存し取得する
- **THEN** JSON として保存され、取得時に元の構造へ復元される

### Requirement: Secret を保存しない

storage capability は `data-model.md` Sensitive Data Policy の対象（API key, access/refresh token, client secret, private key, cookie, authorization header）を一切保存してはならない（MUST NOT）。

#### Scenario: payload からの secret 混入防止
- **WHEN** AdminCommand payload に secret 相当のフィールドが含まれる入力が来る
- **THEN** storage 層は secret を保存対象に含めない（呼び出し側でのサニタイズを前提とし、schema に secret 用列を持たない）
