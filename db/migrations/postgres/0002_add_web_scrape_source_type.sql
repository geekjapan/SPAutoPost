-- PostgreSQL: 'web_scrape' を source_records.source_type の CHECK 制約に追加する。
--
-- 既存の CHECK 制約を DROP して新しい制約を ADD する。
-- PostgreSQL では ALTER TABLE ADD CONSTRAINT が使えるため
-- テーブル再作成は不要。
--
-- migration ランナー契約:
--   - 1 ファイル 1 トランザクションで適用される。
--   - このファイルは既存データを維持したまま制約のみを変更する。

ALTER TABLE source_records
    DROP CONSTRAINT source_records_source_type_check;

ALTER TABLE source_records
    ADD CONSTRAINT source_records_source_type_check
        CHECK (source_type IN (
            'manual', 'nvd', 'myjvn', 'kev', 'vendor', 'rss', 'external_collector', 'web_scrape'
        ));
