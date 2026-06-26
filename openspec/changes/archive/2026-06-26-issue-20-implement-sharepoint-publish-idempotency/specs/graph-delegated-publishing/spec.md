## ADDED Requirements

### Requirement: SharePointPagesClient Protocol に update_site_page を追加する

`SharePointPagesClient` Protocol は `update_site_page` メソッドを持たなければならない（SHALL）。これにより、リトライ時に既存 SharePoint ページのコンテンツを更新できる。

```python
def update_site_page(
    self, *, site_id: str, page_id: str, request_body: Mapping[str, Any], access_token: str
) -> None: ...
```

Graph API: `PATCH /sites/{siteId}/pages/{pageId}/microsoft.graph.sitePage`

#### Scenario: update_site_page が既存ページを上書きする

- **WHEN** `update_site_page` が既存の `page_id` で呼ばれる
- **THEN** Graph API の PATCH エンドポイントにリクエスト本文を送信し、ページコンテンツを更新する

#### Scenario: update_site_page 失敗は error_code にマッピングされる

- **WHEN** `update_site_page` が Graph エラーを受け取る
- **THEN** `_failure_details` と同じエラーコードマッピングで `failed` Publication を記録する
