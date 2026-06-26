# Microsoft Graph Authentication Specification

## Status

Accepted for M0（#27 確定済み）

## Purpose

この Spec は、SPAutoPost が Microsoft Graph を通じて SharePoint Site Page / News article を作成、更新、下書き、公開するための認証・認可方式を定義します。

## Decisions

1. Admin UI/API login は Microsoft Entra ID を利用する。
2. **Local PoC / 初期疎通では delegated permission（Device Code Flow）を採用する。**
3. **Azure hosted runtime では user-assigned managed identity を採用する（第一候補）。**
4. **user-assigned managed identity で組織的・技術的制約がある場合のみ、application permission / app-only access を fallback として使用する。**
5. **Delegated permission は Azure hosted scheduled job（本番定期実行）の認証方式にしない。**
6. **Graph permission は `Sites.Selected` を優先し、投稿に必要な最小セットのみ付与する。**
7. **SharePoint 投稿対象 site は設定ファイルで明示的に指定し、任意 URL への投稿を禁止する。**
8. AuditEvent には approve した user principal と publish を実行した service identity の両方を記録する。

## Context

SPAutoPost の運用コアは Azure Container Apps / Azure Container Apps Jobs に置きます。

SharePoint 投稿処理は、人間ユーザーの端末ではなく、Azure 上の実行環境から Microsoft Graph を呼び出します。

組織では Azure、SharePoint、SPAutoPost Admin UI/API のログイン認証に Microsoft Entra ID を利用できます。

ただし、Admin UI/API に管理者が Entra ID でログインすることと、SPAutoPost の scheduled job / publisher が Microsoft Graph を呼び出すことは別の認証問題として扱います。

## Authentication Layers

### Layer 1: Admin user login

管理者、reviewer、approver、publisher が Admin UI/API にログインするための認証です。

方針:

- Microsoft Entra ID を利用する。
- 詳細は `docs/specs/admin-authentication.md` に定義する。
- 管理者操作は user principal として AuditEvent に記録する。

### Layer 2: Graph service authentication

SPAutoPost が Microsoft Graph を呼び出して SharePoint Site Page / News を作成・更新・公開するための認証です。

方針:

- **Local PoC**: delegated permission（Device Code Flow）を採用する。開発者がブラウザで Entra ID 認証を完了し、取得したトークンで Graph を呼び出す。
- **Azure hosted runtime**: user-assigned managed identity を採用する（第一候補）。
- **hosted runtime での fallback**: managed identity への Graph permission 付与が組織ポリシー上不可能な場合のみ、application permission / app-only access（client credentials flow）を使用する。
- **本番定期実行**: delegated permission は使用しない。ユーザーのブラウザセッション・refresh token の生存に依存する認証を定期実行に採用しない。

## Decided Models

### Local PoC: Delegated permission（Device Code Flow）

ユーザーがサインインし、そのユーザーの権限で Microsoft Graph を呼び出す方式です。

**決定内容（local PoC）**:

- **採用**。Device Code Flow を使用する。
- 開発者端末でブラウザ認証を完了し、取得した access token / refresh token で Graph を呼び出す。
- token は OS 標準の token cache または MSAL の token cache に保存し、repo にはコミットしない。
- 当面は一般公開しないため、投稿者として個人アカウントが見えることを許容する。
- **Azure hosted scheduled job の本番認証には使用しない。**

### Azure hosted runtime: User-assigned managed identity（第一候補）

Azure Container Apps / Jobs で利用する managed identity です。

**決定内容（Azure hosted runtime）**:

- **採用**（user-assigned を選択）。
- Container Apps App と Container Apps Jobs で同一の user-assigned managed identity を共有する。
- system-assigned managed identity は採用しない（resource 単位で identity が分散するため）。
- Secret を持たない運用を実現する。
- `azure-identity` の `ManagedIdentityCredential(client_id=<UAMI_CLIENT_ID>)` で実装し、UAMI の client ID を明示的に指定する。`client_id` を省略すると system-assigned identity にフォールバックするため省略禁止。
- `DefaultAzureCredential` は Graph 認証に使用しない。`DefaultAzureCredential` は環境変数のサービスプリンシパル（`AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET`）を managed identity より先に試みるため、app-only fallback の環境変数が設定されている場合に誤った identity で Graph を呼び出す。
- UAMI の client ID は設定ファイルまたは環境変数から取得し、コードに直書きしない。
- M1 で `Sites.Selected` permission の付与可否を検証する。

### Azure hosted runtime fallback: Application permission / app-only access

アプリケーション自身の identity で Microsoft Graph を呼び出す方式です。

**決定内容（fallback）**:

- **managed identity への Graph permission 付与が組織ポリシー上不可能であると M1 検証で確認された場合のみ採用する。**
- client credentials flow（client secret または certificate）を使用する。
- Secret は Azure Key Vault に保管し、repo にはコミットしない。
- 最小権限化と対象 site 限定を前提にする。

## Graph Permissions

### 最小化方針

- `Sites.Selected` を優先して使用し、投稿対象の SharePoint site のみにアクセス権を限定する。
- `Sites.ReadWrite.All`、`Sites.FullControl.All` 等の tenant 全体に影響する permission は使用しない。
- permission は app registration または managed identity ごとに decision record / runbook に記録する。
- 本番用 app registration と開発用 app registration を分離する。

### 暫定 permission セット（M1 検証対象）

#### Local PoC（delegated permission / Device Code Flow）

| Permission | 種別 | 用途 |
|---|---|---|
| `Sites.ReadWrite.All` | Delegated（work/school） | Site Page / News 記事の作成・更新（Microsoft Docs 記載の最小 delegated 権限） |

`Pages.ReadWrite.All` は sitePage create API の delegated permission として記載されていない（[Microsoft Graph permissions reference](https://learn.microsoft.com/en-us/graph/api/sitepage-create?view=graph-rest-1.0#permissions)）。local PoC で `Sites.ReadWrite.All`（Delegated）を付与することで Device Code Flow 経由のページ作成が可能になる。**注意**: Delegated `Sites.ReadWrite.All` は local PoC 限定。Azure hosted scheduled job の本番認証には使用しない。

#### Azure hosted runtime（application permission / managed identity）

| Permission | 種別 | 用途 |
|---|---|---|
| `Sites.Selected` | Application | 対象 site への読み書きスコープ限定（推奨） |
| `Pages.ReadWrite.All` | Application | Site Page / News 記事の作成・更新（Sites.Selected 対応状況による、M1 検証） |

**Sites.Selected の追加手順**: `Sites.Selected` を Entra アプリ permission として付与するだけではどの site にもアクセスできない。アプリに `Sites.Selected` を付与した後、`POST /sites/{siteid}/permissions` で対象 site に対するロール（例: `write`）を個別に割り当てる必要がある（[Microsoft Docs: selected permissions overview](https://learn.microsoft.com/en-us/graph/permissions-selected-overview)）。M1 では managed identity への `Sites.Selected` 付与と、`sharepoint.site_id` に対する per-site grant の両方を検証する。

**M1 で確認すること**: `Sites.Selected` + `Pages.ReadWrite.All`（Application）の組み合わせで Site Page / News の作成・更新・公開が可能か。`Pages.ReadWrite.All` が site page 作成に対応していない場合（Microsoft Docs では `Sites.ReadWrite.All` が application permission として記載されている）、`Sites.ReadWrite.All` を例外的に採用し decision record に理由を記録する。**注意**: `Sites.ReadWrite.All` は tenant 全体に有効な permission であり、`Sites.Selected` を同時に付与しても `Sites.ReadWrite.All` のスコープは限定されない。`Sites.ReadWrite.All` フォールバック採用時の補完制御として、アプリケーションレベルで投稿先を `sharepoint.site_id` に限定し、すべての Graph 呼び出しを audit log に記録することを必須とする。

## SharePoint 対象範囲の限定

- 投稿対象 SharePoint site は設定ファイル（`sharepoint.site_id`）で明示的に指定する。
- 設定ファイルに記載されていない site への投稿は拒否し、audit log に記録する。
- 任意 URL への投稿は禁止する。
- `Sites.Selected` のみを使用する場合、付与対象 site 以外への Graph API アクセスは API レベルで拒否される。`Sites.ReadWrite.All` フォールバック採用時はこの API レベルの拒否は機能しないため、アプリケーションレベルの制御と audit log を補完制御として必須とする。

## Required Follow-ups（M1）

- user-assigned managed identity に `Sites.Selected` permission を付与できるか確認する。
- `Sites.Selected` + `Pages.ReadWrite.All` の組み合わせで Site Page / News の作成・更新・公開が可能かを検証する。不可能な場合は `Sites.ReadWrite.All` の例外採用と decision record 記録を行う。
- application permission / app-only fallback を使う条件（managed identity 不可）を M1 終了時に確定する。
- approve した user principal と publish を実行した service identity を AuditEvent にどう保存するかを設計する。

## Security Requirements

- Secret を repo に保存しない。
- token cache は OS 標準の cache または MSAL token cache に保存し、repo ファイルには書き込まない。
- 投稿対象 site / page library を設定ファイルで固定し、任意 URL への投稿を禁止する。
- Graph permission は `Sites.Selected` 優先で最小権限にする。
- 投稿前承認（DraftPost の approved フラグ）を必須にする。
- approve した user principal と publish を実行した service identity の両方を AuditEvent に記録する。

## Related Issues

- #2 Confirm SharePoint announcement board contract
- #9 Implement SharePoint connector proof-of-concept
- #24 Finalize Azure hosted core architecture
- #26 Define minimal admin review API and UI boundary
- #27 Decide Microsoft Graph authentication model
- #32 Implement local Graph delegated posting PoC
