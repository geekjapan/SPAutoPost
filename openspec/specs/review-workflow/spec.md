# review-workflow Specification

## Purpose
TBD - created by archiving change issue-19-implement-review-approval-workflow. Update Purpose after archive.
## Requirements
### Requirement: 合法的な状態遷移のみ受理する

システムは以下の遷移のみを受理しなければならない（SHALL）。それ以外の遷移は `InvalidTransitionError` を送出して拒否しなければならない（SHALL）。

| 遷移元 | アクション | 遷移先 |
|--------|-----------|--------|
| `created` | `request_review` | `review_requested` |
| `generated` | `request_review` | `review_requested` |
| `regeneration_requested` | `request_review` | `review_requested` |
| `review_requested` | `comment` | `reviewed` |
| `review_requested` | `approve` | `approved` |
| `review_requested` | `reject` | `rejected` |
| `review_requested` | `request_regeneration` | `regeneration_requested` |
| `reviewed` | `approve` | `approved` |
| `reviewed` | `reject` | `rejected` |
| `reviewed` | `request_regeneration` | `regeneration_requested` |

#### Scenario: 有効な遷移は受理される
- **WHEN** `generated` 状態の DraftPost に `request_review` アクションを適用する
- **THEN** 遷移先 `review_requested` が返される

#### Scenario: 不正な遷移は拒否される
- **WHEN** `approved` 状態の DraftPost に `request_review` アクションを適用する
- **THEN** `InvalidTransitionError` が送出される（previous_status, action, attempted status を含む）

#### Scenario: `published` 状態からはいかなる遷移も拒否される
- **WHEN** `published` 状態の DraftPost に任意のレビューアクションを適用する
- **THEN** `InvalidTransitionError` が送出される

### Requirement: reviewer comment と approval metadata を記録する

システムは遷移ごとに `ReviewEvent` を作成しなければならない（SHALL）。`ReviewEvent` には `reviewer`・`action`・`created_at`・`previous_status`・`next_status` を含めなければならない（SHALL）。

#### Scenario: approve アクションの記録
- **WHEN** reviewer が DraftPost を承認する
- **THEN** `action="approve"`・`previous_status`・`next_status="approved"` を含む `ReviewEvent` が生成される

#### Scenario: reject アクションの記録
- **WHEN** reviewer が DraftPost を却下する
- **THEN** `action="reject"`・`next_status="rejected"` を含む `ReviewEvent` が生成される

#### Scenario: regeneration request の記録
- **WHEN** reviewer が再生成を要求する
- **THEN** `action="request_regeneration"`・`next_status="regeneration_requested"` を含む `ReviewEvent` が生成される

#### Scenario: comment は comment フィールドに記録される
- **WHEN** reviewer がコメント付きでレビューする
- **THEN** `ReviewEvent.comment` にそのコメント文字列が保持される

### Requirement: approved でない DraftPost は publish できない

システムは `status != "approved"` の DraftPost の publish を拒否しなければならない（SHALL）。`dry_run=True` の場合も同様に拒否しなければならない（SHALL）。

#### Scenario: approved DraftPost は publish ゲートを通過する
- **WHEN** `status="approved"` の DraftPost に対して publish を試みる
- **THEN** publish ゲートは通過する（エラーなし）

#### Scenario: approved でない DraftPost は publish ゲートで拒否される
- **WHEN** `status="generated"` の DraftPost に対して publish を試みる
- **THEN** `PublishGateError` が送出される（draft_id と actual_status を含む）

#### Scenario: dry_run でも publish ゲートは有効
- **WHEN** `dry_run=True` で `status="review_requested"` の DraftPost に対して publish を試みる
- **THEN** `PublishGateError` が送出される

### Requirement: regeneration request を扱える

システムは `request_regeneration` アクションを受理し、DraftPost を `regeneration_requested` 状態へ遷移させ、`ReviewEvent` を記録しなければならない（SHALL）。

#### Scenario: 再生成要求の遷移
- **WHEN** `review_requested` 状態の DraftPost に `request_regeneration` アクションを適用する
- **THEN** 遷移先 `regeneration_requested` が返される

#### Scenario: regeneration_requested からの再レビュー
- **WHEN** `regeneration_requested` 状態の DraftPost に `request_review` アクションを適用する
- **THEN** 遷移先 `review_requested` が返される

