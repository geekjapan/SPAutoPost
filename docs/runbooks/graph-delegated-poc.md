# Runbook: ローカル Graph delegated 投稿 PoC

Issue #32 の PoC。手元環境で delegated permission（device code flow）を使い Microsoft Graph
経由で SharePoint Site Page を作成する疎通確認手順。**ローカル PoC 専用**で、hosted runtime の
本番認証方式（managed identity / app-only）は対象外（決定は Issue #27 /
`docs/specs/graph-authentication.md`）。

当面は一般公開しないため、投稿者として個人アカウント（サインインした user principal）が
見えることを許容する。投稿者は `AuditEvent.actor` に記録される。

## 前提

- Python 3.12+ と本リポジトリの dev セットアップ（`pip install -e ".[dev,graph]"`）。
  `graph` extra が `msal` を入れる。
- 投稿先の専用 SharePoint site と page library がある。
- Microsoft Entra ID で **public client** アプリ（device code flow 用）を 1 つ登録できる権限。

## 1. public client アプリ登録（Entra ID）

1. Entra ID > App registrations > New registration。
2. Supported account types は組織の方針に合わせる（単一テナント推奨）。
3. Authentication > Advanced settings > **Allow public client flows** を **Yes** にする
   （device code flow に必要）。client secret は不要。
4. API permissions > Microsoft Graph > **Delegated** > `Sites.ReadWrite.All` を追加し、
   必要なら管理者同意を与える。
   - 最小権限の upgrade path: 将来 app-only / managed identity へ移行する際は
     `Sites.Selected` + 対象 site への grant に絞る（`docs/specs/graph-authentication.md`）。
5. 控える値: **Application (client) ID**、**Directory (tenant) ID**、投稿先の **site ID** と
   **page library ID**。

## 2. 環境変数（Secret は env のみ。repo / config に値を書かない）

```sh
export SPAUTOPOST_TENANT_ID=<tenant-id>
export SPAUTOPOST_GRAPH_CLIENT_ID=<public-client-app-id>
export SPAUTOPOST_SHAREPOINT_SITE_ID=<site-id>
export SPAUTOPOST_SHAREPOINT_PAGE_LIBRARY_ID=<page-library-id>
```

`config.example.yml` を `config/default.yml` にコピーし、`graph` / `sharepoint` セクションが
上記 env を参照していることを確認する（`config/*.yml` は gitignore 対象）。

## 3. dry-run（既定・外部投稿しない）

```sh
spautopost --config-dir ./config publish-draft samples/advisories/manual-cve.yaml
```

- 認証・Graph 呼び出しは行わない。投稿予定 payload を組み立て、`Publication`
  （`publication_status=dry_run`）と `AuditEvent`（`event_type=publish_dry_run`）を記録する。
- 出力 JSON では `env:` 参照・Secret は `***` に redaction される。

## 4. 実投稿（疎通確認・delegated device code）

```sh
spautopost --config-dir ./config --no-dry-run publish-draft samples/advisories/manual-cve.yaml
```

- 端末に device code とサインイン URL が表示される。ブラウザで URL を開き、表示コードを入力して
  サインインする。
- 成功すると Site Page が作成され、`Publication`（`published`、`sharepoint_page_id` 付き）と
  `AuditEvent`（`publish_create`、`actor`=サインイン user principal、`service_principal`=client_id）
  が記録される。
- News として publish（promote）まで行う場合は `--promote` を付ける（任意段）。
- 失敗時は `Publication`（`failed`、`error_code` / `retryable`）と `AuditEvent`（`error`）が記録され、
  コマンドは非ゼロ終了する。access token 等の Secret は記録・表示されない。

## 5. 冪等性

同一 draft・同一投稿先で既に `published` / `publishing` の `Publication` がある場合、再実行しても
新規 Graph 作成は行わず既存 `Publication` を返す（`idempotency_key` による重複投稿防止）。

## スコープ外 / 次のステップ

- hosted runtime の本番認証方式（user-assigned managed identity を第一候補、app-only を代替）は
  本 PoC では決定・実装しない。Issue #27 に残す。
- 本番公開、複数 site 投稿、添付・画像、複雑な page layout は対象外。
