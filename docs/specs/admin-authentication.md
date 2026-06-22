# Admin Authentication Specification

## Status

Accepted for MVP direction. Proposed for detailed authorization model.

## Purpose

この Spec は、SPAutoPost の Admin API / UI にログインする管理者ユーザーの認証方式、認可方針、監査要件を定義します。

## Decision

SPAutoPost の Admin API / UI のログイン認証は、組織の Microsoft Entra ID 連携を利用します。

Azure、SharePoint、SPAutoPost 管理画面の認証基盤は、一律 Microsoft Entra ID を前提とします。

## Scope

対象:

- Admin API / UI へのログイン
- 管理者ユーザーの識別
- reviewer / approver / publisher 操作の監査
- Entra ID group / role による初期認可
- Azure Container Apps Authentication / Microsoft identity platform の利用方針

非対象:

- Microsoft Graph の service-to-service 認証方式の最終決定
- SharePoint Site Page / News への投稿権限の最終 grant
- 複雑な多段 RBAC
- 外部利用者向け認証

## Authentication Model

MVP では次を前提にします。

- Identity Provider: Microsoft Entra ID
- Target: SPAutoPost Admin API / UI
- Login Users: 組織内の管理者、セキュリティ担当者、掲示板運用担当者
- Session / token handling: Azure Container Apps Authentication または Admin API 側の OIDC integration を候補とする

## Authorization Model

MVP の最小 role:

- viewer: DraftPost と AuditEvent を閲覧できる
- reviewer: DraftPost を確認し、コメント・修正要求できる
- approver: DraftPost を approve / reject できる
- publisher: approved DraftPost の投稿要求を出せる
- admin: 設定と管理操作ができる

MVP では、Entra ID group または app role による単純な認可を候補とします。

複雑な RBAC、多段承認、代理承認は MVP 対象外です。

## Audit Requirements

Admin 操作では、次を AuditEvent に記録します。

- user principal id
- user principal name
- display name if available
- role / group decision if available
- action
- draft_id / publication_id
- previous_status
- next_status
- timestamp
- correlation_id

ログに出してはいけない項目:

- access token
- refresh token
- id token raw value
- cookie
- authorization header

## Relationship to Microsoft Graph Authentication

Admin API / UI のログイン認証と、SPAutoPost が Microsoft Graph を呼び出すサービス認証は分けて扱います。

- Admin login: Microsoft Entra ID user authentication
- Graph call for SharePoint publishing: managed identity / application permission / delegated permission を別途比較する

管理者が Entra ID でログインして approve したとしても、そのユーザーの delegated token を定期 job が利用するとは限りません。

## Candidate Implementation

### Option A: Azure Container Apps Authentication

Azure Container Apps の built-in authentication を使い、Microsoft Entra ID で Admin API / UI を保護する方式です。

利点:

- アプリケーションコードから認証処理を分離しやすい
- Container Apps と相性がよい
- 認証済みユーザー情報を request headers 経由で取得できる

懸念:

- 詳細な認可はアプリケーション側で実装が必要
- ローカル開発時の代替認証が必要

### Option B: Admin API 側で OIDC integration

Admin API / UI 側で Microsoft identity platform / OIDC を直接扱う方式です。

利点:

- アプリケーション側で認証・認可フローを細かく制御できる
- UI / API の構成に合わせやすい

懸念:

- 実装量とセキュリティレビュー負荷が増える

## Preliminary Recommendation

MVP では、Azure Container Apps Authentication + Microsoft Entra ID を第一候補とします。

ただし、TypeScript / Node.js Admin UI / API の採用範囲によっては、OIDC integration を直接実装する案も残します。

## Open Questions

- Admin API / UI を M1 で Python 側に最小実装するか、TypeScript / Node.js を M1 から入れるか
- Entra ID group と app role のどちらで reviewer / approver / publisher を表現するか
- Azure Container Apps Authentication を使うか、アプリ側 OIDC を使うか
- ローカル開発時の admin authentication をどう扱うか

## Related Issues

- #26 Define minimal admin review API and UI boundary
- #27 Decide Microsoft Graph authentication model
