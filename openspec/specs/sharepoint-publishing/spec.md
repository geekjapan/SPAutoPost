# Capability: SharePoint Publishing

## Purpose

SPAutoPost が SharePoint お知らせ掲示板に自動投稿するための発行機能を定義する。投稿形式・認証方式・設定項目・ライフサイクル・制約（M1 スコープ）を規定する。

## Requirements

### Requirement: 投稿先は SharePoint Site Page / News article とする

SPAutoPost は SharePoint お知らせ掲示板への投稿に SharePoint Site Page / News article 形式を使用しなければならない（SHALL）。SharePoint List item は M1 の主経路に含まない。

#### Scenario: Site Page として投稿が作成される
- **WHEN** 管理者が承認済み DraftPost の投稿を指示する
- **THEN** Graph API `/sites/{siteId}/pages`（sitePage エンドポイント）を使用して Site Page が作成される

#### Scenario: List item への投稿は拒否される
- **WHEN** 設定 `sharepoint.mode` が `site-page` 以外の値に設定される
- **THEN** システムは起動時バリデーションエラーを返し、投稿を行わない

### Requirement: Graph 権限は最小権限セットを使用する

SPAutoPost が使用する Microsoft Graph 権限は以下の最小権限セットでなければならない（SHALL）。

- Azure hosted runtime（application permission）:
  - `Sites.Selected`（推奨）または `Sites.ReadWrite.All`（初期セットアップ暫定）
  - 必要に応じて `Files.ReadWrite.All`
- ローカル PoC（delegated permission）:
  - `Sites.ReadWrite.All`

SPAutoPost はこれらの権限以外を要求してはならない（SHALL NOT）。

#### Scenario: managed identity で Azure hosted 動作する
- **WHEN** `SPAUTOPOST_AUTH_METHOD=managed-identity` が設定されている
- **THEN** アプリケーションはクライアントシークレットなしで Graph API に接続し、設定済みの application permission で動作する

#### Scenario: delegated permission でローカル PoC 動作する
- **WHEN** `SPAUTOPOST_AUTH_METHOD=delegated` が設定されている
- **THEN** アプリケーションは対話型認証フローで Graph API に接続する

### Requirement: 投稿先設定項目を完全定義する

SharePoint 投稿先は以下の設定項目で指定しなければならない（SHALL）。任意 URL への動的投稿は許可しない。

```yaml
sharepoint:
  mode: site-page                           # 必須: "site-page" 固定
  tenant_id: env:SPAUTOPOST_TENANT_ID       # 必須
  site_id: env:SPAUTOPOST_SHAREPOINT_SITE_ID  # 必須
  page_library_id: env:SPAUTOPOST_SHAREPOINT_PAGE_LIBRARY_ID  # 必須
  dedicated_site: true                      # 必須: 専用サイトのみ許可
  default_draft: true                       # 必須: デフォルトは下書き
  allow_publish: false                      # M1: SPAutoPost からの公開は行わない
  news_promote: false                       # M1: News promote は非対象
  idempotency_scope: site-and-page-library  # 必須
security:
  require_approval: true                    # 必須: 管理者承認後のみ投稿可
```

#### Scenario: 必須設定が欠けている場合は起動失敗する
- **WHEN** `tenant_id`、`site_id`、`page_library_id` のいずれかが未設定
- **THEN** アプリケーションは起動時に設定バリデーションエラーを返す

#### Scenario: 設定が完全な場合は起動する
- **WHEN** 上記全必須項目が設定されている
- **THEN** アプリケーションは正常に起動し Graph API 接続を試みる

### Requirement: 下書き作成のみ行い SPAutoPost からの公開は M1 非対象とする

M1 では SPAutoPost は SharePoint Site Page を下書き（`draft`）状態で作成しなければならない（SHALL）。SPAutoPost から `publish` エンドポイント（`/sites/{siteId}/pages/{pageId}/publish`）を呼ぶことは M1 では禁止する（SHALL NOT）。

公開は SharePoint 画面から管理者が手動で行う、または SharePoint 側の承認フローに委ねる。

#### Scenario: 投稿後ページは下書き状態になる
- **WHEN** 投稿処理が完了する
- **THEN** 作成された SharePoint page の状態は `draft` であり、SharePoint 上で未公開の状態になる

#### Scenario: SPAutoPost は publish を呼ばない
- **WHEN** `allow_publish: false` が設定されている（M1 デフォルト）
- **THEN** Graph API publish エンドポイントは呼び出されず、ログに `publish skipped (M1)` が記録される

### Requirement: News promote は M1 スコープ外とする

M1 では News article としての promote（`PromoteNewsArticle` 相当の操作）は実装してはならない（SHALL NOT）。

#### Scenario: News promote は呼び出されない
- **WHEN** `news_promote: false` が設定されている（M1 デフォルト）
- **THEN** Graph API の News promote エンドポイントは呼び出されない

### Requirement: 公開範囲は SharePoint サイト設定に委ねる

SPAutoPost は投稿した Site Page のアクセス権限を変更してはならない（SHALL NOT）。公開範囲は対象 SharePoint サイトの既存アクセス権設定に従う。

#### Scenario: アクセス権の変更は行わない
- **WHEN** Site Page が作成される
- **THEN** SPAutoPost はページのアクセス権変更 API を呼び出さない

### Requirement: 投稿ライフサイクルと失敗時動作を定義する

投稿処理は以下のライフサイクルに従わなければならない（SHALL）。

状態遷移:
1. `pending` → 投稿キュー待機
2. `publishing` → Graph API 呼び出し中
3. `published` → 作成成功（下書き状態の page が存在する）
4. `dry_run` → dry-run モードで実行（作成・更新なし）
5. `skipped` → 冪等性チェックにより作成スキップ
6. `failed` → エラー発生

エラーコード:
- `authentication_failed` / `authorization_failed` → 非 retryable
- `target_not_found` / `page_library_not_found` → 非 retryable
- `required_field_missing` → 非 retryable
- `graph_rate_limited` → retryable（exponential backoff）
- `graph_timeout` → retryable
- `duplicate_detected` → 非 retryable（idempotency_key 一致、`skipped` 状態へ遷移）

#### Scenario: 認証失敗は即座に失敗する
- **WHEN** Graph API が 401 を返す
- **THEN** Publication.status が `failed`、error_code が `authentication_failed`、retryable が `false` に設定される

#### Scenario: レート制限は自動リトライする
- **WHEN** Graph API が 429 を返す
- **THEN** Publication.status が `failed`、retryable が `true`、error_code が `graph_rate_limited` に設定され、retry policy に従い再試行される

#### Scenario: 重複投稿は idempotency_key で検出する
- **WHEN** 同一 idempotency_key の Publication が `published` 状態で既存する
- **THEN** 新規 Graph API 呼び出しは行われず、既存 Publication への参照が返る

### Requirement: 添付ファイルと画像は M1 非対象とする

M1 では投稿コンテンツは本文テキストのみとしなければならない（SHALL）。添付ファイルや画像の投稿は M1 スコープ外とする。

#### Scenario: テキストのみの投稿が成功する
- **WHEN** DraftPost が本文テキストのみで構成されている
- **THEN** Graph API を使用して Site Page が正常に作成される

#### Scenario: 添付ファイル付き投稿は受け付けない
- **WHEN** DraftPost に添付ファイルが含まれている
- **THEN** バリデーションエラーが返され、投稿は実行されない（M1 非対応として明示）
