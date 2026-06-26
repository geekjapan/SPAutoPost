## Context

- `DraftPost.status` は `DraftStatus` Literal で型付け済み（`storage/models.py`）。  
- `ReviewEvent` / `ReviewAction` DTO も既存（append-only）。  
- `graph/publisher.py` はすでに `StoragePort` を受け取り `Publication` / `AuditEvent` を記録する。  
- `sharepoint-publishing` spec に `security.require_approval: true` が定義されているが、コードレベルの publish ゲートがない。

## Goals / Non-Goals

**Goals**
- `DraftPost` の合法的な状態遷移のみ受理する純粋関数として `ReviewService` を実装する。
- publish 前に `approved` を強制するゲート関数を作り、`publisher.py` から呼ぶ。
- `ReviewEvent` を都度 `StoragePort` に append し監査証跡を保証する。

**Non-Goals**
- 多段承認・RBAC・Teams 通知・ITSM 連携は本 change 外。
- `DraftPost` の DB スキーマ変更なし（既存フィールドで十分）。
- Admin API / UI の変更なし。

## Decisions

### D1: ReviewService は純粋な状態機械関数群とする

`ReviewService` クラスは StoragePort に依存しない純粋関数群（`transition()` / `assert_publishable()`）として実装し、呼び出し側（job / admin API handler）が Storage 操作を担う。

代替: サービスクラスが StoragePort を持つ → テストでモックが必要になり複雑。純粋関数なら `pytest` で DI 不要。

### D2: 不正遷移は `InvalidTransitionError`、publish ゲート違反は `PublishGateError`

両例外は `errors.py` に追加。`publisher.py` は `PublishGateError` を `dry_run` ゲートの前に投げ（呼び出し側が catch）、`failed` Publication としては記録しない（設計不変条件の違反であり retryable でないため）。

代替: `PublishError` の subclass → 既存の Graph エラーコードと混在して混乱を招くので分離。

### D3: 状態遷移テーブル（許可される遷移のみ）

```
created            → review_requested   (action: request_review)
generated          → review_requested   (action: request_review)
regeneration_requested → review_requested (action: request_review)
review_requested   → reviewed           (action: comment)
review_requested   → approved           (action: approve)
review_requested   → rejected           (action: reject)
review_requested   → regeneration_requested (action: request_regeneration)
reviewed           → approved           (action: approve)
reviewed           → rejected           (action: reject)
reviewed           → regeneration_requested (action: request_regeneration)
```

上記以外は `InvalidTransitionError`（previous_status / action / attempted next_status を含む）。

### D4: `publisher.py` 統合は最小限の hook

`publish_site_page()` の先頭（`dry_run` 分岐の前）で `assert_publishable(draft_status)` を呼ぶ。`dry_run=True` でもゲートを通す（ドライランでも承認が必要）。

## Risks / Trade-offs

- [リスク] `reviewer` / `review_comments` は `DraftPost` の optional フィールドとして既存するが、本 change では `ReviewEvent` への append を正規の記録場所とし `DraftPost` の重複フィールドは更新しない。→ 将来的な整合性は別 issue で検討。
- [リスク] `DraftPost` は frozen dataclass のため状態更新は replace（新インスタンス生成）が必要。呼び出し側は `dataclasses.replace()` を使う。ReviewService はその責務を持たない（純粋関数のため）。

## Migration Plan

既存 DB スキーマ変更なし。`storage/migrate.py` への追加不要。

## Open Questions

なし（全て D1-D4 で解決済み）。
