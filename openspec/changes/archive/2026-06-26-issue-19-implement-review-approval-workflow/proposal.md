## Why

DraftPost の生成後、承認なしに SharePoint へ投稿できる状態を防ぐため、レビュー・承認ワークフローが必要。`sharepoint-publishing` spec の `security.require_approval: true` を実装レベルで保証する publish ゲートがまだ存在しない（Issue #19, M4）。

## What Changes

- `DraftPost` 状態遷移ロジック（`review_requested` → `reviewed` → `approved` / `rejected` / `regeneration_requested`）を `ReviewService` として実装する
- 不正な状態遷移は `InvalidTransitionError` で明示拒否する
- reviewer comment と approval metadata（誰が/いつ/結果）を `ReviewEvent` に記録する
- publish ゲート関数を実装し、`approved` 以外の DraftPost を投稿しようとした場合に明示エラーを返す
- `graph/publisher.py` に publish ゲートを統合する
- 状態遷移・publish ゲートの単体テスト一式を追加する

## Capabilities

### New Capabilities

- `review-workflow`: DraftPost のレビュー・承認状態遷移と publish ゲートを定義する

### Modified Capabilities

- `sharepoint-publishing`: `security.require_approval: true` の実装保証（publish ゲート強制）をシナリオとして追記する

## Impact

- 新規: `src/spautopost/review_workflow.py`（状態遷移・publish ゲート）
- 変更: `src/spautopost/graph/publisher.py`（publish ゲートの統合）
- 変更: `src/spautopost/errors.py`（`InvalidTransitionError`・`PublishGateError` 追加）
- 新規: `tests/test_review_workflow.py`
- 変更: `tests/graph/test_publisher.py`（ゲートテスト追加）
- 既存 `storage/models.py` の `DraftStatus` / `ReviewEvent` / `ReviewAction` はそのまま流用（変更なし）
