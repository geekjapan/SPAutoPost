# Microsoft Graph Authentication Specification

## Status

Decided（Issue #27 で全受け入れ条件を確定）

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
- `azure-identity` の `ManagedIdentityCredential` または `DefaultAzureCredential` で実装する。
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

| Permission | 種別 | 用途 |
|---|---|---|
| `Sites.Selected` | Application | 対象 site への読み書きスコープ限定（推奨） |
| `Pages.ReadWrite.All` | Application | Site Page / News 記事の作成・更新（Sites.Selected 対応状況による） |

**M1 で確認すること**: `Sites.Selected` + `Pages.ReadWrite.All` の組み合わせで Site Page / News の作成・更新・公開が可能か。不可能な場合は代替 permission を評価する。

## SharePoint 対象範囲の限定

- 投稿対象 SharePoint site URL は設定ファイル（`sharepoint.site_url`）で明示的に指定する。
- 設定ファイルに記載されていない site への投稿は拒否し、audit log に記録する。
- 任意 URL への投稿は禁止する。
- `Sites.Selected` permission によって、付与対象 site 以外への Graph API アクセスは API レベルでも拒否される。

## Required Follow-ups（M1）

- user-assigned managed identity に `Sites.Selected` permission を付与できるか確認する。
- `Sites.Selected` + `Pages.ReadWrite.All` の組み合わせで Site Page / News の作成・更新・公開が可能かを検証する。
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
