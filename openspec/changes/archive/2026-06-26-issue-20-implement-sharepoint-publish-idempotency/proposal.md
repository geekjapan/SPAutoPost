## Why

`publisher.py` は既に `idempotency_key` 生成と `published/publishing` スキップを持つが、  
`pending` / `publishing` 中間状態を実際には書き込まず、かつ先行失敗で `sharepoint_page_id` が存在する場合のリトライで CREATE を再度呼ぶため二重ページが発生しうる。  
Issue #20 はこのギャップを埋め、Publication の状態遷移を完全にし、リトライ時の create vs update 判定を実装する。

## What Changes

- `publisher.py`: live publish 開始前に `pending`、Graph API 呼び出し直前に `publishing` を upsert する
- `publisher.py`: リトライ時、既存 Publication に `sharepoint_page_id` がある場合は `update_site_page` を呼び、ない場合は `create_site_page` を呼ぶ（create vs update 判定）
- `sharepoint_client.py`: `SharePointPagesClient` Protocol に `update_site_page` メソッドを追加、`GraphSharePointPagesClient` に PATCH 実装を追加
- テスト: 状態遷移・リトライシナリオ（page あり / page なし）・失敗ケースを追加

## Capabilities

### New Capabilities

なし（既存 spec 要件を実装する）

### Modified Capabilities

- `sharepoint-publishing`: pending / publishing 中間状態の実際の設定を明示。リトライ時の create vs update 判断基準（`sharepoint_page_id` 有無）を追加。
- `graph-delegated-publishing`: リトライ時に update 経路が存在することを追記。

## Impact

- `src/spautopost/graph/publisher.py`（状態遷移追加・retry 判定）
- `src/spautopost/graph/sharepoint_client.py`（Protocol + 実装に `update_site_page` 追加）
- `tests/graph/conftest.py`（FakePagesClient に update_calls 追加）
- `tests/graph/test_publisher.py`（新テスト追加）
- 既存の他テストへの影響なし（追加のみ、破壊的変更なし）
