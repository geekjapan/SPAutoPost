# Tasks: issue-20-implement-sharepoint-publish-idempotency

## Task 1: SharePointPagesClient に update_site_page を追加

- [x] 1.1 `src/spautopost/graph/sharepoint_client.py` の `SharePointPagesClient` Protocol に `update_site_page` を追加
- [x] 1.2 `GraphSharePointPagesClient` に PATCH 実装を追加（`/sites/{siteId}/pages/{pageId}/microsoft.graph.sitePage`）
- [x] 1.3 `tests/graph/conftest.py` の `FakePagesClient` に `update_calls` と `update_site_page` を追加

## Task 2: publisher.py に pending/publishing 状態遷移を追加

- [x] 2.1 live publish 前（idempotency チェック通過後）に `pending` を upsert
- [x] 2.2 token 取得後・API 呼び出し前に `publishing` を upsert
- [x] 2.3 既存の `published` / `failed` upsert はそのまま維持

## Task 3: publisher.py に create vs update リトライ判定を追加

- [x] 3.1 既存 Publication が `failed` かつ `sharepoint_page_id` あり → `update_site_page` を呼ぶ
- [x] 3.2 既存 Publication が `failed` かつ `sharepoint_page_id` なし → 従来通り `create_site_page`
- [x] 3.3 update 成功時: `operation="update"` で `published` を記録
- [x] 3.4 update 失敗時: `operation="update"` で `failed` を記録
- [x] 3.5 promote=True の場合、update 経路でも `publish_site_page` を呼び `operation="publish"` に更新

## Task 4: テスト追加

- [x] 4.1 `test_pending_then_publishing_then_published`: pending→publishing 遷移を acquire() / create_site_page() の両フックで検証
- [x] 4.2 `test_retry_with_existing_page_id_calls_update`: failed + sharepoint_page_id ありでリトライ → update_site_page が呼ばれる
- [x] 4.3 `test_retry_without_page_id_calls_create`: failed + sharepoint_page_id なしでリトライ → create_site_page が呼ばれる
- [x] 4.4 `test_update_failure_records_failed`: update_site_page 失敗が failed Publication を記録する
- [x] 4.5 `test_retry_update_with_promote_calls_publish_site_page`: update 経路で promote=True のとき publish_site_page が呼ばれる

## Task 5: 品質ゲート

- [x] 5.1 `ruff check . && ruff format --check src tests`
- [x] 5.2 `mypy src`
- [x] 5.3 `pytest --cov=spautopost --cov-report=term-missing`（coverage ≥ 80%）
- [x] 5.4 既存テストがすべてパスすること
