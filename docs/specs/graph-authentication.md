# Microsoft Graph Authentication Specification

## Status

Proposed

## Purpose

この Spec は、SPAutoPost が Microsoft Graph を通じて SharePoint Site Page / News article を作成、更新、下書き、公開するための service-to-service 認証・認可方式を比較し、MVP で採用する方式を決めるための論点を整理します。

## Context

SPAutoPost の運用コアは Azure Container Apps / Azure Container Apps Jobs に置きます。

SharePoint 投稿処理は、人間ユーザーの端末ではなく、Azure 上の実行環境から Microsoft Graph を呼び出します。

組織では Azure、SharePoint、SPAutoPost Admin UI/API のログイン認証に Microsoft Entra ID を利用できます。

ただし、Admin UI/API に管理者が Entra ID でログインすることと、SPAutoPost の scheduled job / publisher が Microsoft Graph を呼び出すことは別の認証問題として扱います。

## Authentication Layers

### Layer 1: Admin user login

管理者、reviewer、approver、publisher が Admin UI/API にログインするための認証です。

方針:

- Microsoft Entra ID を利用する
- 詳細は `docs/specs/admin-authentication.md` に定義する
- 管理者操作は user principal として AuditEvent に記録する

### Layer 2: Graph service authentication

SPAutoPost が Microsoft Graph を呼び出して SharePoint Site Page / News を作成・更新・公開するための認証です。

方針:

- ユーザー端末や個人ユーザーの常時ログイン状態に依存しない
- Azure hosted runtime から安全に実行できる方式を採用する
- managed identity / application permission / delegated permission を比較する

## Candidate Models

### Option A: Delegated permission

ユーザーがサインインし、そのユーザーの権限で Microsoft Graph を呼び出す方式です。

利点:

- 実際の管理者権限に近い動作を検証しやすい
- 初期 PoC で理解しやすい
- SharePoint 側のユーザー権限と整合しやすい

懸念:

- 定期実行や unattended job と相性が悪い
- token 管理、refresh、管理者不在時の実行継続が難しい
- ユーザー退職・異動・権限変更の影響を受ける
- 管理者が approve したことと、同じ管理者 token で publisher が動くことを混同しやすい

MVP での扱い:

- ローカル PoC または手動検証用途としては候補
- Azure hosted scheduled job の本命にはしない

### Option B: Application permission / app-only access

アプリケーション自身の identity で Microsoft Graph を呼び出す方式です。

利点:

- Azure Jobs / background service と相性がよい
- ユーザーサインインに依存しない
- 定期収集・投稿処理に向く
- 監査対象を service principal として整理しやすい

懸念:

- 権限が広くなりやすい
- admin consent が必要
- SharePoint site / page library への権限限定を慎重に設計する必要がある

MVP での扱い:

- Azure hosted core の本命候補
- 最小権限化と対象 site 限定を前提に採用可否を判断する

### Option C: Managed identity

Azure Container Apps / Jobs の managed identity を使って Azure / Microsoft Entra protected resources にアクセスする方式です。

利点:

- client secret を持たずに済む
- Azure hosted runtime と相性がよい
- credential rotation の運用負荷を下げられる
- Azure resource access では標準的に扱いやすい

懸念:

- Microsoft Graph / SharePoint Site Page 操作に必要な application permission 付与の具体手順を検証する必要がある
- local development との切替が必要
- system-assigned / user-assigned identity のどちらを使うか決める必要がある

MVP での扱い:

- 本番方向の有力候補
- M1 では app registration / service principal と比較し、検証可能性を確認する

### Option D: Hybrid

Admin login は Entra ID、ローカル PoC は delegated、Azure hosted runtime は application permission または managed identity を使う方式です。

利点:

- 初期検証を速く進められる
- 本番運用はユーザー端末に依存しない
- 管理者の承認操作と publisher の実行 identity を分離できる

懸念:

- 認証方式が複数になり、設定とテストが複雑になる
- PoC と本番で権限差分が出やすい

MVP での扱い:

- 現実的な移行案
- ただし本番方向の正本は application permission / managed identity に寄せる

## Preliminary Recommendation

現時点の推奨は次のとおりです。

1. Admin UI/API login: Microsoft Entra ID
2. Local PoC / 初期疎通: delegated permission を許容
3. Azure hosted core / scheduled jobs: app-only access または managed identity を本命にする
4. 本番方向: managed identity + site/page library scope の最小権限化を第一候補として検証する

## Required Decisions

MVP 実装前に決めること:

- ローカル PoC で delegated permission を使うか
- Azure hosted runtime で app registration + client credential を使うか、managed identity を使うか
- system-assigned managed identity と user-assigned managed identity のどちらを使うか
- SharePoint site / page library の権限をどの単位で限定するか
- admin consent の取得手順をどうするか
- Graph permission と SharePoint site permission の監査方法
- Admin user の approve と service principal / managed identity の publish をどう紐づけて監査するか

## Security Requirements

- Secret を repo に保存しない
- client secret より certificate / federated credential / managed identity を優先する
- 投稿対象 site / page library を限定する
- Graph permission は最小権限にする
- app-only access の利用範囲を SharePoint 投稿に限定する
- 投稿前承認を必須にする
- approve した user principal と publish を実行した service identity の両方を AuditEvent に記録する

## Related Issues

- #2 Confirm SharePoint announcement board contract
- #9 Implement SharePoint connector proof-of-concept
- #24 Finalize Azure hosted core architecture
- #26 Define minimal admin review API and UI boundary
- #27 Decide Microsoft Graph authentication model
