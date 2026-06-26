## ADDED Requirements

### Requirement: Delegated device code authentication for local PoC

local PoC では、システムは Microsoft Graph への delegated 認証を device code flow で取得し、サインインしたユーザーの identity（user principal name と表示名）を access token と一緒に呼び出し側へ返す SHALL。認証は `GraphTokenProvider` Protocol に抽象化し、実装の差し替え（実 MSAL / テスト fake）を可能にする SHALL。Secret（client secret 等）は要求せず、`client_id` と `tenant_id` のみで public client として動作する SHALL。

#### Scenario: Device code 認証がユーザー identity を返す

- **WHEN** `GraphTokenProvider.acquire` が呼ばれ、ユーザーが device code で正常にサインインする
- **THEN** access token と、サインインしたユーザーの user principal name・表示名を含む `Identity` を返す

#### Scenario: 認証経路は注入で差し替えできる

- **WHEN** publisher にテスト用の fake `GraphTokenProvider` を注入する
- **THEN** 実 MSAL や network 呼び出しなしに publisher の認証段が動作する

### Requirement: Site Page をビルドして Graph へ投稿する

システムは生成済み draft の Site Page payload から Graph の Site Page 作成リクエスト本文を組み立て、`SharePointPagesClient` を通じて作成し、応答から SharePoint page ID を取得する SHALL。リクエスト本文の組み立てと応答からの page ID 抽出は、network I/O から分離した純関数として実装し、単体テスト可能にする SHALL。クライアントは `SharePointPagesClient` Protocol に抽象化する SHALL。

#### Scenario: payload から Graph リクエスト本文を組み立てる

- **WHEN** dry-run で組み立てた Site Page payload を Graph リクエストビルダに渡す
- **THEN** title と必須セクションを含む Graph Site Page リソース本文を返す（network 呼び出しなし）

#### Scenario: 応答から page ID を抽出する

- **WHEN** Graph の Site Page 作成応答 JSON を受け取る
- **THEN** SharePoint page ID を抽出して返す

### Requirement: dry-run は外部投稿を行わない

`publish_site_page` は dry-run のとき、認証・Graph 呼び出し・実投稿を一切行わず SHALL NOT、投稿予定 payload の組み立てと、`dry_run` 状態の `Publication`・`publish_dry_run` の `AuditEvent` の記録のみを行う SHALL。dry-run は既定動作とし、明示的な opt-out（`--no-dry-run`）でのみ実投稿経路に入る SHALL。

#### Scenario: dry-run では Graph を呼ばない

- **WHEN** dry-run で `publish_site_page` を実行する
- **THEN** token provider と pages client は呼び出されず、`publication_status` が `dry_run` の `Publication` と `publish_dry_run` の `AuditEvent` が記録される

#### Scenario: 既定は dry-run

- **WHEN** CLI の `publish-draft` を `--no-dry-run` なしで実行する
- **THEN** dry-run として扱われ、外部投稿は行われない

### Requirement: 投稿結果を Publication として記録する

`publish_site_page` は投稿結果を `Publication` として `StoragePort` 経由で記録する SHALL。`Publication` は `idempotency_key`（draft_id・target_site_id・target_page_library_id・advisory_ids・正規化 title から決定論的に生成）を持ち、同一キーの再実行では新規作成せず既存 `Publication` を返す SHALL。実投稿成功時は `published`、失敗時は `failed` と `error_code` / `error_message` / `retryable` を記録する SHALL。

#### Scenario: 実投稿成功で published を記録する

- **WHEN** `--no-dry-run` で `publish_site_page` が Site Page 作成に成功する
- **THEN** `publication_status` が `published`、`sharepoint_page_id` が設定された `Publication` が記録される

#### Scenario: 投稿失敗で failed を記録する

- **WHEN** pages client が Graph エラーを送出する
- **THEN** `publication_status` が `failed`、`error_code` と `retryable` を含む `Publication` が記録され、例外は呼び出し側へ伝播しない

#### Scenario: idempotency_key で重複投稿を防ぐ

- **WHEN** 同一 draft・同一投稿先で既に `published` な `Publication` が存在する状態で再実行する
- **THEN** 新規の Graph 作成は行わず、既存 `Publication` を返す

### Requirement: 投稿者情報を AuditEvent に記録する

システムは投稿処理を `AuditEvent` として `StoragePort` 経由で記録する SHALL。delegated 実投稿では、サインインした user principal を `actor`、登録アプリ（client_id）を `service_principal` として記録する SHALL。`event_type` は audit-log.md の値（dry-run は `publish_dry_run`、作成は `publish_create`、結果は `publish_result`、失敗は `error`）を使い、Secret / token を `AuditEvent` に含めない SHALL NOT。

#### Scenario: 実投稿で投稿者を記録する

- **WHEN** delegated 認証で実投稿が成功する
- **THEN** `actor` がサインインした user principal name、`service_principal` が client_id の `AuditEvent` が記録される

#### Scenario: AuditEvent に Secret を含めない

- **WHEN** 認証または投稿で `AuditEvent` を記録する
- **THEN** access token・refresh token・client secret 等の Secret は `AuditEvent` のどのフィールドにも含まれない

### Requirement: hosted 本番認証方式は本 PoC の対象外

本 change は local PoC の delegated 経路のみを実装し、hosted runtime の本番認証方式（user-assigned managed identity / app-only）は決定も実装もしない SHALL NOT。hosted 本番認証方式の決定は Issue #27 に残す SHALL。

#### Scenario: hosted 認証は未実装で #27 へ委ねる

- **WHEN** `graph.hosted_auth` 設定や hosted 用 identity を参照する
- **THEN** 本 change では実装されず、決定は #27 に委ねられていることが runbook / spec から確認できる
