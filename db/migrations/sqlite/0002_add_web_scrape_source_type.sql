-- SQLite: 'web_scrape' を source_records.source_type の CHECK 制約に追加する。
--
-- SQLite は ALTER TABLE ADD CONSTRAINT をサポートしないため、
-- テーブルを再作成してデータを移行する方式をとる。
-- (参考: https://www.sqlite.org/lang_altertable.html)
--
-- advisories.source_record_id が source_records へ FK を持つため、
-- PRAGMA foreign_keys=ON のままでは DROP TABLE が FOREIGN KEY constraint failed で失敗する。
-- 公式推奨パターン (https://www.sqlite.org/foreignkeys.html#fk_schemacommands):
--   FK 制約をいったん無効化してからテーブルを再作成し、
--   コミット後にバックエンド/呼び出し元が FK を再有効化する。
--
-- 重要 — PRAGMA と transaction の相互作用:
--   PRAGMA foreign_keys はトランザクション内では no-op になる (SQLite 仕様)。
--   このファイルの先頭文を PRAGMA にすることで、migration ランナーが最初の文を
--   実行する時点ではまだトランザクションが開始されていないことを利用する。
--   FK の再有効化は COMMIT 後に SQLiteBackend が PRAGMA foreign_keys=ON で行う。
--
-- migration ランナー契約:
--   - 1 ファイル 1 トランザクションで適用される。
--   - このファイルは既存データを維持したまま制約のみを変更する。

PRAGMA foreign_keys=OFF;

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
