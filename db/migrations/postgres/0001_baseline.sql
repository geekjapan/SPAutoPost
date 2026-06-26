-- SPAutoPost baseline schema (PostgreSQL 正本方言)。
--
-- 正本: docs/specs/data-model.md / docs/specs/audit-log.md /
--       docs/specs/sharepoint-publishing.md と
--       openspec/changes/issue-28-implement-postgresql-storage-baseline/specs/storage-schema。
--
-- SQLite backend (db/migrations/sqlite/0001_baseline.sql) との等価性:
--   - 同一のテーブル集合・列集合・CHECK enum 集合・FK 集合・UNIQUE index 集合。
--   - 型は方言マッピング: TEXT/TEXT/REAL <- JSONB/timestamptz/numeric。
--   - JSON は JSONB、timestamp は timestamptz、bool は boolean で格納する。
--   - 等価性は tests/storage/test_schema_equivalence.py が構造的にガードする。
--
-- 重要 (migration ランナー契約):
--   - このファイルは 1 ファイル 1 トランザクションで適用される。
--   - 非トランザクション DDL (例: CREATE INDEX CONCURRENTLY) を含めてはならない。
--     ランナーが BEGIN/COMMIT で包むため CONCURRENTLY は使用不可。
--   - schema_migrations テーブルはランナーがブートストラップするため、ここでは作らない。

-- 6 番目のルートエンティティ: 外部情報源・手動入力の生データ記録。
CREATE TABLE source_records (
    source_record_id TEXT PRIMARY KEY,
    source_type      TEXT NOT NULL
        CHECK (source_type IN (
            'manual', 'nvd', 'myjvn', 'kev', 'vendor', 'rss', 'external_collector'
        )),
    source_name      TEXT NOT NULL,
    retrieved_at     TIMESTAMPTZ NOT NULL,
    raw_hash         TEXT NOT NULL,
    parser_version   TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL,
    source_url       TEXT,
    raw_payload_ref  TEXT,
    http_status      INTEGER,
    etag             TEXT,
    last_modified    TEXT,
    error_code       TEXT,
    error_message    TEXT
);

-- 正規化済み脆弱性・注意喚起データ。
CREATE TABLE advisories (
    advisory_id         TEXT PRIMARY KEY,
    title               TEXT NOT NULL,
    summary             TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL,
    normalized_at       TIMESTAMPTZ NOT NULL,
    source_record_id    TEXT,
    published_at        TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ,
    severity            TEXT NOT NULL DEFAULT 'unknown'
        CHECK (severity IN ('critical', 'high', 'medium', 'low', 'unknown')),
    cve_ids             JSONB NOT NULL DEFAULT '[]',
    jvn_ids             JSONB NOT NULL DEFAULT '[]',
    vendor_advisory_ids JSONB NOT NULL DEFAULT '[]',
    cvss_version        TEXT,
    cvss_score          NUMERIC,
    cvss_vector         TEXT,
    "references"        JSONB NOT NULL DEFAULT '[]',
    tags                JSONB NOT NULL DEFAULT '[]',
    FOREIGN KEY (source_record_id) REFERENCES source_records (source_record_id)
);

-- FK 列のインデックス (spec ルール: FK は常にインデックス化する)。
CREATE INDEX ix_advisories_source_record_id ON advisories (source_record_id);

-- SharePoint 掲示板向け原稿。summary_for_users / impact は NOT NULL。
CREATE TABLE draft_posts (
    draft_id              TEXT PRIMARY KEY,
    title                 TEXT NOT NULL,
    audience              TEXT NOT NULL
        CHECK (audience IN ('general_users', 'administrators', 'mixed')),
    urgency               TEXT NOT NULL
        CHECK (urgency IN ('emergency', 'high', 'normal', 'low')),
    summary_for_users     TEXT NOT NULL,
    impact                TEXT NOT NULL,
    status                TEXT NOT NULL
        CHECK (status IN (
            'created', 'generated', 'review_requested', 'reviewed', 'approved',
            'rejected', 'regeneration_requested', 'publishing', 'published',
            'failed', 'cancelled'
        )),
    created_at            TIMESTAMPTZ NOT NULL,
    updated_at            TIMESTAMPTZ NOT NULL,
    advisory_id           TEXT,
    advisory_ids          JSONB NOT NULL DEFAULT '[]',
    required_actions      JSONB NOT NULL DEFAULT '[]',
    admin_actions         JSONB NOT NULL DEFAULT '[]',
    "references"          JSONB NOT NULL DEFAULT '[]',
    deadline              TIMESTAMPTZ,
    generated_by_provider TEXT,
    prompt_version        TEXT,
    generation_input_hash TEXT,
    validation_warnings   JSONB NOT NULL DEFAULT '[]',
    reviewer              TEXT,
    review_comments       JSONB NOT NULL DEFAULT '[]',
    FOREIGN KEY (advisory_id) REFERENCES advisories (advisory_id)
);

-- FK 列のインデックス (spec ルール: FK は常にインデックス化する)。
CREATE INDEX ix_draft_posts_advisory_id ON draft_posts (advisory_id);

-- レビュー・承認履歴 (append-only)。
CREATE TABLE review_events (
    review_event_id TEXT PRIMARY KEY,
    draft_id        TEXT NOT NULL,
    reviewer        TEXT NOT NULL,
    action          TEXT NOT NULL
        CHECK (action IN (
            'request_review', 'comment', 'approve', 'reject', 'request_regeneration'
        )),
    created_at      TIMESTAMPTZ NOT NULL,
    comment         TEXT,
    previous_status TEXT
        CHECK (previous_status IS NULL OR previous_status IN (
            'created', 'generated', 'review_requested', 'reviewed', 'approved',
            'rejected', 'regeneration_requested', 'publishing', 'published',
            'failed', 'cancelled'
        )),
    next_status     TEXT
        CHECK (next_status IS NULL OR next_status IN (
            'created', 'generated', 'review_requested', 'reviewed', 'approved',
            'rejected', 'regeneration_requested', 'publishing', 'published',
            'failed', 'cancelled'
        )),
    FOREIGN KEY (draft_id) REFERENCES draft_posts (draft_id)
);

-- FK 列のインデックス (spec ルール: FK は常にインデックス化する)。
CREATE INDEX ix_review_events_draft_id ON review_events (draft_id);

-- SharePoint 投稿結果。idempotency_key は NOT NULL + UNIQUE。
CREATE TABLE publications (
    publication_id          TEXT PRIMARY KEY,
    draft_id                TEXT NOT NULL,
    target_type             TEXT NOT NULL
        CHECK (target_type IN ('list-item', 'site-page')),
    target_site_id          TEXT NOT NULL,
    publication_status      TEXT NOT NULL
        CHECK (publication_status IN (
            'pending', 'dry_run', 'publishing', 'published', 'failed', 'skipped'
        )),
    idempotency_key         TEXT NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL,
    updated_at              TIMESTAMPTZ NOT NULL,
    target_list_id          TEXT,
    target_page_library_id  TEXT,
    sharepoint_item_id      TEXT,
    sharepoint_page_id      TEXT,
    operation               TEXT
        CHECK (operation IS NULL OR operation IN (
            'dry-run', 'create', 'update', 'publish'
        )),
    published_at            TIMESTAMPTZ,
    error_code              TEXT,
    error_message           TEXT,
    retryable               BOOLEAN
        CHECK (retryable IS NULL OR retryable IN (FALSE, TRUE)),
    FOREIGN KEY (draft_id) REFERENCES draft_posts (draft_id)
);

-- idempotency_key の重複投稿を DB 層で封鎖する UNIQUE index。
-- NOT NULL 列上の UNIQUE のため、PostgreSQL の複数 NULL すり抜けは発生しない。
CREATE UNIQUE INDEX ux_publications_idempotency_key
    ON publications (idempotency_key);

-- FK 列のインデックス (spec ルール: FK は常にインデックス化する)。
CREATE INDEX ix_publications_draft_id ON publications (draft_id);

-- 監査・障害対応・説明責任イベント (append-only)。
-- event_type は audit-log.md の 15 値で CHECK 制約。
CREATE TABLE audit_events (
    audit_event_id         TEXT PRIMARY KEY,
    event_type             TEXT NOT NULL
        CHECK (event_type IN (
            'source_fetch', 'source_parse', 'normalize', 'triage',
            'draft_generate', 'draft_validate', 'review', 'approve', 'reject',
            'regenerate', 'publish_dry_run', 'publish_create', 'publish_update',
            'publish_result', 'error'
        )),
    correlation_id         TEXT NOT NULL,
    result                 TEXT NOT NULL
        CHECK (result IN ('success', 'failure', 'skipped', 'warning')),
    created_at             TIMESTAMPTZ NOT NULL,
    actor                  TEXT,
    service_principal      TEXT,
    related_ids            JSONB,
    source_name            TEXT,
    provider_name          TEXT,
    provider_type          TEXT,
    prompt_version         TEXT,
    target_site_id         TEXT,
    target_list_id         TEXT,
    target_page_library_id TEXT,
    sharepoint_item_id     TEXT,
    sharepoint_page_id     TEXT,
    idempotency_key        TEXT,
    operation              TEXT
        CHECK (operation IS NULL OR operation IN (
            'dry-run', 'create', 'update', 'publish'
        )),
    error_code             TEXT,
    error_message          TEXT
);

-- Admin UI/API から Python core への非同期 command inbox。
-- payload は JSONB だが Secret は storage 境界で拒否する。
CREATE TABLE admin_commands (
    command_id      TEXT PRIMARY KEY,
    command_type    TEXT NOT NULL
        CHECK (command_type IN (
            'edit', 'approve', 'reject', 'request_regeneration', 'publish_request'
        )),
    target_draft_id TEXT,
    requested_by    TEXT,
    payload         JSONB NOT NULL DEFAULT '{}',
    idempotency_key TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'succeeded', 'failed', 'cancelled')),
    error_code      TEXT,
    error_message   TEXT,
    correlation_id  TEXT,
    created_at      TIMESTAMPTZ NOT NULL,
    processed_at    TIMESTAMPTZ,
    FOREIGN KEY (target_draft_id) REFERENCES draft_posts (draft_id)
);

CREATE UNIQUE INDEX ux_admin_commands_idempotency_key
    ON admin_commands (idempotency_key);

CREATE INDEX ix_admin_commands_status ON admin_commands (status);
CREATE INDEX ix_admin_commands_target_draft_id ON admin_commands (target_draft_id);
