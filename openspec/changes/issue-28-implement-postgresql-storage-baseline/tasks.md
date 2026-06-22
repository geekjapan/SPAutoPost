## 1. Python ランタイム最小初期化

- [ ] 1.1 Python プロジェクト雛形を作成（パッケージ構成、依存管理ファイル、PostgreSQL driver と test 依存）
- [ ] 1.2 `DATABASE_URL` 等の接続設定読み込みを最小実装（secret はログに出さない）
- [ ] 1.3 test ランナーと storage テスト用 SQLite/PostgreSQL fixture を用意

## 2. SQL migration baseline（schema 正本）

- [ ] 2.1 `db/migrations` に baseline migration を作成し、canonical entity（SourceRecord, Advisory, DraftPost, ReviewEvent, Publication, AuditEvent）テーブルを定義
- [ ] 2.2 AdminCommand/Intent テーブルを定義（status/idempotency_key/correlation_id/processed_at 等）
- [ ] 2.3 enum 類を TEXT + CHECK 制約で定義（DraftStatus 11 状態、severity, publication_status, command status 等）
- [ ] 2.4 queryable 列の index、idempotency_key の UNIQUE（Publication / AdminCommand）、draft_id の FK を定義
- [ ] 2.5 配列/ネスト属性を JSON（PG JSONB）列として定義
- [ ] 2.6 同一論理 schema から SQLite 互換 DDL を派生

## 3. storage port と adapter

- [ ] 3.1 Python 所有 storage port を定義（entity read/write stores のインターフェース）
- [ ] 3.2 command queue 操作を port に追加（append_command / claim_pending_commands / complete_command / fail_command）
- [ ] 3.3 PostgreSQL adapter を実装（claim は FOR UPDATE SKIP LOCKED、JSONB、timestamptz）
- [ ] 3.4 SQLite adapter を実装（JSON text、ISO8601 UTC TEXT、port が UTC 正規化）
- [ ] 3.5 canonical model 表現を追加（schema を参照する薄い entity 定義）

## 4. テスト（TDD）

- [ ] 4.1 baseline migration 適用テスト（全テーブル/制約/index 生成）
- [ ] 4.2 entity round-trip テスト（保存→取得一致、JSON ネスト復元）
- [ ] 4.3 CHECK 制約テスト（DraftStatus enum 外の値を拒否）
- [ ] 4.4 UNIQUE テスト（重複 Publication / AdminCommand idempotency_key 拒否）
- [ ] 4.5 command queue テスト（排他 claim / complete / fail、SKIP LOCKED 挙動）
- [ ] 4.6 PostgreSQL adapter と SQLite adapter が同一 port API で同一結果を返すことの確認

## 5. 検証と仕上げ

- [ ] 5.1 lint / 型検査 / テストを実行し green を確認
- [ ] 5.2 secret 非保存（Sensitive Data Policy）を満たすことを確認
- [ ] 5.3 受け入れ条件（Issue #28）と spec scenario の充足を確認
