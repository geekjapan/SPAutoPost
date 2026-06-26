## ADDED Requirements

### Requirement: 投稿前に pending 状態を記録する

システムは live publish（dry-run 以外）を開始する前に、`publication_status = "pending"` の Publication を upsert しなければならない（SHALL）。これにより、Graph API 呼び出し前に処理開始が記録される。

#### Scenario: live publish 開始前に pending が書き込まれる

- **WHEN** `publish_site_page` が `dry_run=False` で呼ばれ、idempotency チェックを通過する
- **THEN** Graph API 呼び出し前に `publication_status = "pending"` の Publication が storage に upsert される

### Requirement: Graph API 呼び出し直前に publishing 状態に遷移する

システムは token 取得後、Graph API 呼び出しの直前に `publication_status = "publishing"` の Publication を upsert しなければならない（SHALL）。

#### Scenario: token 取得後に publishing が書き込まれる

- **WHEN** `GraphTokenProvider.acquire()` が成功し、API 呼び出し直前の状態
- **THEN** `publication_status = "publishing"` の Publication が storage に upsert される

### Requirement: リトライ時に create vs update を判定する

システムはリトライ時（既存 Publication が `failed` 状態）に、`sharepoint_page_id` の有無に基づいて create と update を判定しなければならない（SHALL）。

- `sharepoint_page_id` が設定済みの場合: SharePoint の既存ページを UPDATE する
- `sharepoint_page_id` が未設定の場合: SharePoint に新規ページを CREATE する

これにより、ページが既に作成されている場合の二重投稿を防ぐ（SHALL）。

#### Scenario: 部分失敗後のリトライで update が選択される

- **WHEN** 既存 Publication の `publication_status = "failed"` かつ `sharepoint_page_id` が設定されている
- **THEN** Graph API の `create_site_page` は呼ばれず、`update_site_page` が呼ばれる

#### Scenario: ページ未作成の失敗後のリトライで create が選択される

- **WHEN** 既存 Publication の `publication_status = "failed"` かつ `sharepoint_page_id` が未設定
- **THEN** `create_site_page` が呼ばれる
