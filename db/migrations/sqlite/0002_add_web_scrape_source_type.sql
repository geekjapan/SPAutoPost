-- SQLite: 'web_scrape' を source_records.source_type の CHECK 制約に追加する。
--
-- SQLite は ALTER TABLE ADD CONSTRAINT をサポートしないため、
-- テーブルを再作成してデータを移行する方式をとる。
-- (参考: https://www.sqlite.org/lang_altertable.html)
--
-- migration ランナー契約:
--   - 1 ファイル 1 トランザクションで適用される。
--   - このファイルは既存データを維持したまま制約のみを変更する。

CREATE TABLE source_records_new (
    source_record_id TEXT PRIMARY KEY,
    source_type      TEXT NOT NULL
        CHECK (source_type IN (
            'manual', 'nvd', 'myjvn', 'kev', 'vendor', 'rss', 'external_collector', 'web_scrape'
        )),
    source_name      TEXT NOT NULL,
    retrieved_at     TEXT NOT NULL,
    raw_hash         TEXT NOT NULL,
    parser_version   TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    source_url       TEXT,
    raw_payload_ref  TEXT,
    http_status      INTEGER,
    etag             TEXT,
    last_modified    TEXT,
    error_code       TEXT,
    error_message    TEXT
);

INSERT INTO source_records_new SELECT * FROM source_records;

DROP TABLE source_records;

ALTER TABLE source_records_new RENAME TO source_records;
