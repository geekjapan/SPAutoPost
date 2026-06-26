-- SPAutoPost storage baseline (SQLite = local/test 互換 adapter)
-- PostgreSQL 正本（db/migrations/postgres/0001_baseline.sql）と同一論理 schema。
-- 差分のみ: timestamptz -> TEXT(ISO8601 UTC、port が正規化)、JSONB -> TEXT(JSON1)。
-- enum=TEXT+CHECK、UNIQUE/CHECK/FK/index は同一。FK は接続側で PRAGMA foreign_keys=ON。

CREATE TABLE source_records (
  source_record_id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL CHECK (source_type IN ('manual','nvd','myjvn','kev','vendor','rss','external_collector')),
  retrieved_at TEXT NOT NULL,
  raw_hash TEXT NOT NULL,
  parser_version TEXT NOT NULL,
  attributes TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_source_records_source_type ON source_records (source_type);
CREATE INDEX idx_source_records_retrieved_at ON source_records (retrieved_at);

CREATE TABLE advisories (
  advisory_id TEXT PRIMARY KEY,
  severity TEXT CHECK (severity IN ('critical','high','medium','low','unknown')),
  created_at TEXT NOT NULL,
  normalized_at TEXT NOT NULL,
  published_at TEXT,
  updated_at TEXT,
  attributes TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_advisories_severity ON advisories (severity);
CREATE INDEX idx_advisories_created_at ON advisories (created_at);

CREATE TABLE draft_posts (
  draft_id TEXT PRIMARY KEY,
  status TEXT NOT NULL CHECK (status IN ('created','generated','review_requested','reviewed','approved','rejected','regeneration_requested','publishing','published','failed','cancelled')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  attributes TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_draft_posts_status ON draft_posts (status);

CREATE TABLE review_events (
  review_event_id TEXT PRIMARY KEY,
  draft_id TEXT NOT NULL REFERENCES draft_posts (draft_id),
  action TEXT NOT NULL CHECK (action IN ('request_review','comment','approve','reject','request_regeneration')),
  created_at TEXT NOT NULL,
  attributes TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_review_events_draft_id ON review_events (draft_id);

CREATE TABLE publications (
  publication_id TEXT PRIMARY KEY,
  draft_id TEXT NOT NULL REFERENCES draft_posts (draft_id),
  publication_status TEXT NOT NULL CHECK (publication_status IN ('pending','dry_run','publishing','published','failed','skipped')),
  idempotency_key TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  attributes TEXT NOT NULL DEFAULT '{}',
  CONSTRAINT uq_publications_idempotency_key UNIQUE (idempotency_key)
);
CREATE INDEX idx_publications_draft_id ON publications (draft_id);
CREATE INDEX idx_publications_publication_status ON publications (publication_status);

CREATE TABLE audit_events (
  audit_event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL CHECK (event_type IN ('source_fetch','normalize','draft_generate','validate','review','approve','publish','error')),
  correlation_id TEXT NOT NULL,
  result TEXT NOT NULL CHECK (result IN ('success','failure','skipped','warning')),
  created_at TEXT NOT NULL,
  attributes TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_audit_events_correlation_id ON audit_events (correlation_id);
CREATE INDEX idx_audit_events_event_type ON audit_events (event_type);

CREATE TABLE admin_commands (
  command_id TEXT PRIMARY KEY,
  command_type TEXT NOT NULL CHECK (command_type IN ('edit','approve','reject','request_regeneration','publish_request')),
  target_draft_id TEXT REFERENCES draft_posts (draft_id) ON DELETE CASCADE,
  requested_by TEXT,
  payload TEXT NOT NULL DEFAULT '{}',
  idempotency_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','succeeded','failed','cancelled')),
  error_code TEXT,
  error_message TEXT,
  correlation_id TEXT,
  created_at TEXT NOT NULL,
  processed_at TEXT,
  CONSTRAINT uq_admin_commands_idempotency_key UNIQUE (idempotency_key)
);
CREATE INDEX idx_admin_commands_status ON admin_commands (status);
CREATE INDEX idx_admin_commands_target_draft_id ON admin_commands (target_draft_id);
