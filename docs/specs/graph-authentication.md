# Microsoft Graph Authentication Specification

## Status

Accepted for local PoC and target hosted strategy.

## Purpose

この Spec は、SPAutoPost が Microsoft Graph を通じて SharePoint Site Page / News article を作成、更新、下書き、公開するための認証・認可方式を定義します。

## Decisions

1. Admin UI/API login は Microsoft Entra ID を利用する。
2. Local PoC / 初期疎通では delegated permission を許容する。
3. Azure hosted runtime では user-assigned managed identity を第一候補とする。
4. user-assigned managed identity で実装上の制約が大きい場合、application permission / app-only access を代替候補とする。
5. Delegated permission は Azure hosted scheduled job の本命方式にはしない。
6. SharePoint site / page library の権限は可能な範囲で限定する。
7. AuditEvent には approve した user principal と publish を実行した service identity の両方を記録する。

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

- Local PoC は delegated permission を許容する。
- Azure hosted runtime は user-assigned managed identity を第一候補とする。
- application permission / app-only access は代替候補とする。
- hosted runtime ではユーザー端末や個人ユーザーの常時ログイン状態に依存しない。

## Candidate Models

### Option A: Delegated permission

ユーザーがサインインし、そのユーザーの権限で Microsoft Graph を呼び出す方式です。

MVP での扱い:

- local PoC では採用可。
- 当面は一般公開しないため、投稿者として個人アカウントが見えることを許容する。
- Azure hosted scheduled job の本命にはしない。

### Option B: Application permission / app-only access

アプリケーション自身の identity で Microsoft Graph を呼び出す方式です。

MVP での扱い:

- Azure hosted core の代替候補。
- user-assigned managed identity が難しい場合の fallback とする。
- 最小権限化と対象 site 限定を前提にする。

### Option C: User-assigned managed identity

Azure Container Apps / Jobs で利用する managed identity です。

MVP での扱い:

- Azure hosted runtime の第一候補。
- Container Apps App と Jobs で共有しやすい identity として扱う。
- Secret を持たない運用を優先する。
- SharePoint Site Page / News 投稿に必要な Graph 権限付与の具体手順を M1 で検証する。

### Option D: Hybrid

Admin login は Entra ID、ローカル PoC は delegated、Azure hosted runtime は user-assigned managed identity または app-only access を使う方式です。

MVP での扱い:

- 採用する。
- PoC と hosted runtime の認証方式を明確に分離する。

## Required Follow-ups

M1 で確認すること:

- user-assigned managed identity に必要権限を付与できるか。
- SharePoint site / page library の対象範囲をどう限定するか。
- application permission / app-only fallback をどの条件で使うか。
- approve した user principal と publish を実行した service identity を AuditEvent にどう保存するか。

## Security Requirements

- Secret を repo に保存しない。
- 投稿対象 site / page library を限定する。
- Graph permission は最小権限にする。
- 投稿前承認を必須にする。
- approve した user principal と publish を実行した service identity の両方を AuditEvent に記録する。

## Related Issues

- #2 Confirm SharePoint announcement board contract
- #9 Implement SharePoint connector proof-of-concept
- #24 Finalize Azure hosted core architecture
- #26 Define minimal admin review API and UI boundary
- #27 Decide Microsoft Graph authentication model
- #32 Implement local Graph delegated posting PoC
