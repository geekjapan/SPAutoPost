# Admin Authentication with Microsoft Entra ID

## Status

Accepted

## Context

SPAutoPost は、定期収集で作成された記事を管理者が確認し、必要に応じて修正し、確定後に SharePoint Site Page / News として投稿する運用を想定します。

管理者向け UI/API では、組織の既存 ID 基盤と統合し、個別のローカルアカウントや独自認証を持たない方がよいです。

組織では Azure、SharePoint などに一律 Microsoft Entra ID を利用できます。

## Decision

SPAutoPost の Admin API / UI のログイン認証は、Microsoft Entra ID 連携を利用します。

独自ユーザー管理、ローカルアカウント、共有管理者アカウントは採用しません。

## Rationale

- Azure、SharePoint、SPAutoPost の認証基盤を統一できる。
- 管理者操作を user principal として監査しやすい。
- 既存の組織アカウント、MFA、条件付きアクセス、グループ管理と整合しやすい。
- SharePoint 投稿の承認者と操作履歴を紐づけやすい。

## Consequences

- Admin API / UI は Entra ID login を前提に設計する。
- reviewer / approver / publisher / admin の認可は Entra ID group または app role を候補にする。
- Admin login と Graph service authentication は別論点として扱う。
- Graph 投稿処理では、管理者のログイン token をそのまま定期 job の認証に流用しない。
- ローカル開発時の認証 bypass / dev user は、開発専用設定として明示的に制限する。

## Related

- Spec: docs/specs/admin-authentication.md
- Spec: docs/specs/architecture.md
- Spec: docs/specs/graph-authentication.md
- Issue: #26
- Issue: #27
