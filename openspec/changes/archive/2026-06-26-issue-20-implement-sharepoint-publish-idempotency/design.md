# Design: SharePoint Publish Idempotency and State Tracking

## 既存資産との整合

`publisher.py` は既に次を持つ（変更しない）:
- `build_idempotency_key`: 決定論的なキー生成
- `_IDEMPOTENT_STATUSES = ("published", "publishing")`: published/publishing のスキップ
- `assert_publishable`: 承認ゲート
- `_failure_details`: error_code マッピング
- `Publication` upsert による状態記録

本 change はこれを **拡張** する（置き換えない）。

## 状態遷移モデル

```
[初回 live publish]
  → pending (Graph 呼び出し前)
  → publishing (token 取得後、API 呼び出し直前)
  → published (成功) または failed (失敗)

[既存 published/publishing をスキップ]
  → 変更なし（既存動作を維持）

[リトライ: failed, sharepoint_page_id あり]
  → pending
  → publishing
  → UPDATE (既存ページ更新)
  → published または failed

[リトライ: failed, sharepoint_page_id なし]
  → pending
  → publishing
  → CREATE (新規ページ作成)
  → published または failed
```

## Create vs Update 判定ロジック

```python
existing = store.publications.get_by_idempotency_key(key)
if existing and existing.publication_status in _IDEMPOTENT_STATUSES and not dry_run:
    return PublishResult(...)  # skip

# existing.sharepoint_page_id が設定済み → UPDATE 経路
use_update = (existing is not None and existing.sharepoint_page_id is not None
              and existing.publication_status == "failed")
```

## `SharePointPagesClient` Protocol 拡張

```python
def update_site_page(
    self, *, site_id: str, page_id: str, request_body: Mapping[str, Any], access_token: str
) -> None: ...
```

Graph API: `PATCH /sites/{siteId}/pages/{pageId}/microsoft.graph.sitePage`

update は page_id を受け取り既存ページを上書きする。失敗は既存エラーマッピングに従う。

## 状態遷移の実装方針

各状態は `store.publications.upsert` で上書きする（新規 `publication_id` は初回のみ生成、以降は再利用）。

同期実装（async なし）のため:
- `pending`: Graph 呼び出し前に書き込む
- `publishing`: token 取得後・API 呼び出し直前に書き込む
- プロセスクラッシュ時は `publishing` で停止 → 次回リトライは `publishing` ∈ `_IDEMPOTENT_STATUSES` のためスキップされる

`publishing` がスキップ対象であることは既存仕様通り。クラッシュ後の `publishing` 回収は本 Issue スコープ外（管理者が手動リセットまたは将来 Issue で対応）。

## 自己グリル（事前ゲート）

| 懸念 | 判断 |
|------|------|
| `publishing` 中クラッシュで stuck になる | `publishing` はスキップ対象なので意図的な設計。回収は本 Issue 外。 |
| update_site_page の Protocol 追加は破壊的か | fake を更新すれば既存テストへの影響なし。Protocol は追加のみ。 |
| pending 書き込みが失敗した場合 | StorageError は最外のコード側へ伝播（best-effort 吸収対象外）。 |
| dry-run への影響 | dry-run は pending/publishing を書かず、従来通り dry_run で完結。 |
| `update_site_page` が失敗した場合のエラー記録 | 既存 `_failure_details` を流用、`operation="update"` で記録。 |
