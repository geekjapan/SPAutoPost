## ADDED Requirements

### Requirement: approved DraftPost のみ投稿可能

システムは `status=approved` の DraftPost のみ SharePoint Site Page / News article として投稿しなければならない（SHALL）。`approved` 以外の状態の DraftPost に投稿を試みた場合、`PublishError` を送出し、投稿・状態変更・Publication 作成を行ってはならない（SHALL NOT）。

#### Scenario: approved DraftPost を投稿する
- **GIVEN** DraftPost の status が `approved` である
- **WHEN** publish_approved_draft() を呼び出す
- **THEN** システムは Publication を作成し、DraftPost を `publishing` → `published` へ遷移させ、AuditEvent を記録する

#### Scenario: approved でない DraftPost への投稿を拒否する
- **GIVEN** DraftPost の status が `approved` でない（例: `generated`）
- **WHEN** publish_approved_draft() を呼び出す
- **THEN** システムは PublishError を送出し、何も変更しない

### Requirement: 冪等性による重複投稿防止

システムは `idempotency_key`（`draft_id` + `target_site_id` + `target_page_library_id` のハッシュ）で重複投稿を防がなければならない（SHALL）。同一キーで既に `published` または `publishing` の Publication が存在する場合、新規 Graph API 呼び出しを行ってはならない（SHALL NOT）。

#### Scenario: 同一 DraftPost の 2 回目投稿を防ぐ
- **GIVEN** 同一 idempotency_key の Publication が `published` として存在する
- **WHEN** 同じ DraftPost で publish_approved_draft() を再度呼び出す
- **THEN** システムは既存 Publication を返し、新規 Graph API 呼び出しを行わない

### Requirement: Publication と AuditEvent の記録

システムは投稿の試行・成功・失敗をそれぞれ Publication と AuditEvent に記録しなければならない（SHALL）。

- 投稿開始: Publication status = `publishing`、DraftPost status = `publishing`
- 投稿成功: Publication status = `published`、`sharepoint_page_id` を記録、DraftPost status = `published`、AuditEvent `publish_result` / `success`
- 投稿失敗: Publication status = `failed`、`error_code` / `error_message` を記録、DraftPost status = `failed`、AuditEvent `publish_result` / `failure`

#### Scenario: 投稿成功を記録する
- **WHEN** Graph API が成功し SharePoint page が作成される
- **THEN** Publication.publication_status = `published`、DraftPost.status = `published`、AuditEvent.event_type = `publish_result`、result = `success`、sharepoint_page_id が記録される

#### Scenario: 投稿失敗を記録する
- **WHEN** Graph API 呼び出しが例外で失敗する
- **THEN** Publication.publication_status = `failed`、DraftPost.status = `failed`、AuditEvent.event_type = `publish_result`、result = `failure`、error_code が記録される

### Requirement: dry-run では実投稿しない

`dry_run=True` の場合、システムは Graph API 呼び出しを行ってはならない（SHALL NOT）。Publication を `dry_run` status で記録し、AuditEvent `publish_dry_run` / `success` を記録しなければならない（SHALL）。DraftPost の status を変更してはならない（SHALL NOT）。

#### Scenario: dry-run は Graph API を呼び出さない
- **GIVEN** dry_run=True
- **WHEN** publish_approved_draft() を呼び出す
- **THEN** Graph API は呼び出されず、Publication status = `dry_run`、AuditEvent event_type = `publish_dry_run`、DraftPost status は変更されない

### Requirement: Graph 認証情報の安全管理

`MicrosoftGraphClient` は bearer token を環境変数 `SPAUTOPOST_GRAPH_ACCESS_TOKEN` のみから取得しなければならない（SHALL）。token をログ・AuditEvent・Publication に保存してはならない（SHALL NOT）。

#### Scenario: Graph access token が未設定の場合エラー
- **GIVEN** `SPAUTOPOST_GRAPH_ACCESS_TOKEN` が未設定
- **WHEN** MicrosoftGraphClient を初期化する
- **THEN** GraphAuthError を送出する
