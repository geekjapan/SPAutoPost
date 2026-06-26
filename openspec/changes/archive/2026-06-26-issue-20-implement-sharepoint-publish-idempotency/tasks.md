# Tasks: issue-20-implement-sharepoint-publish-idempotency

## Task 1: SharePointPagesClient に update_site_page を追加

- `src/spautopost/graph/sharepoint_client.py` の `SharePointPagesClient` Protocol に `update_site_page` を追加
- `GraphSharePointPagesClient` に PATCH 実装を追加（`/sites/{siteId}/pages/{pageId}/microsoft.graph.sitePage`）
- `tests/graph/conftest.py` の `FakePagesClient` に `update_calls` と `update_site_page` を追加

## Task 2: publisher.py に pending/publishing 状態遷移を追加

- live publish 前（idempotency チェック通過後）に `pending` を upsert
- token 取得後・API 呼び出し前に `publishing` を upsert
- 既存の `published` / `failed` upsert はそのまま維持

## Task 3: publisher.py に create vs update リトライ判定を追加

- 既存 Publication が `failed` かつ `sharepoint_page_id` あり → `update_site_page` を呼ぶ
- 既存 Publication が `failed` かつ `sharepoint_page_id` なし → 従来通り `create_site_page`
- update 成功時: `operation="update"` で `published` を記録
- update 失敗時: `operation="update"` で `failed` を記録

## Task 4: テスト追加

- `test_pending_state_before_graph_call`: live publish 前に pending が書かれること
- `test_publishing_state_before_api_call`: token 取得後に publishing が書かれること（pending→publishing 遷移）
- `test_retry_with_existing_page_id_calls_update`: failed + sharepoint_page_id ありでリトライ → update_site_page が呼ばれる
- `test_retry_without_page_id_calls_create`: failed + sharepoint_page_id なしでリトライ → create_site_page が呼ばれる
- `test_update_failure_records_failed`: update_site_page 失敗が failed Publication を記録する

## Task 5: 品質ゲート

- `ruff check . && ruff format --check src tests`
- `mypy src`
- `pytest --cov=spautopost --cov-report=term-missing`（coverage ≥ 80%）
- 既存テストがすべてパスすること
