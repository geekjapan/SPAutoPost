# Tasks: issue-19-implement-review-approval-workflow

## Phase 1: エラー型追加

- [ ] `src/spautopost/errors.py` に `InvalidTransitionError` と `PublishGateError` を追加する

## Phase 2: ReviewService 実装（TDD）

- [ ] `tests/test_review_workflow.py` に状態遷移テストを先行作成（RED）
- [ ] `tests/test_review_workflow.py` に publish ゲートテストを先行作成（RED）
- [ ] `src/spautopost/review_workflow.py` を実装して全テストを GREEN にする
  - `VALID_TRANSITIONS` 定数（遷移テーブル）
  - `apply_review_action(draft_status, action, reviewer, comment, now, id_factory) -> tuple[DraftStatus, ReviewEvent]`
  - `assert_publishable(draft_id, draft_status) -> None`

## Phase 3: publisher.py 統合

- [ ] `tests/graph/test_publisher.py` に PublishGateError テストを追加（RED）
- [ ] `src/spautopost/graph/publisher.py` の `publish_site_page()` 先頭でゲートを呼ぶ（GREEN）

## Phase 4: 品質ゲート

- [ ] `ruff check . && ruff format --check` を通す
- [ ] `mypy src` を通す
- [ ] `pytest --cov=spautopost --cov-report=term-missing` でカバレッジ 80% 以上を確認

## Phase 5: OpenSpec archive & PR

- [ ] `openspec validate issue-19-implement-review-approval-workflow --strict` を通す
- [ ] `openspec archive issue-19-implement-review-approval-workflow` で specs/ に同期する
- [ ] PR を作成する（マージは coordinator に委ねる）
