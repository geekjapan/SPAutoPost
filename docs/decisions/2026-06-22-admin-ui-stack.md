# Admin UI Stack

## Status

Accepted

## Context

M1 では、生成された DraftPost を管理者が確認、修正、確定し、SharePoint 投稿へ進める Admin UI/API を含めます。

Python core は収集、正規化、記事生成、検証、投稿処理を担います。一方、管理者向け UI/API は TypeScript / Node.js で実装します。

## Decision

M1 の Admin UI/API は TypeScript / Node.js を採用します。

M1 では、単一の Admin App として UI と API をまとめる構成を第一候補とします。

## Rationale

- 管理画面と API を同じ stack で早く実装できる。
- Entra ID login と UI 実装をまとめやすい。
- DraftPost list/detail/edit/approve/publish request の検証に十分である。
- Python core と責務を分けやすい。

## Consequences

- #31 で TypeScript / Node.js Admin UI/API skeleton を実装する。
- #26 で Admin UI/API と Python core の境界を定義する。
- M1 では本格 UI design や複雑な RBAC は対象外とする。
- 将来、必要に応じて frontend と backend API を分離できるようにする。

## Related

- Spec: docs/specs/m1-mvp-scope.md
- Spec: docs/specs/admin-authentication.md
- Issue: #26
- Issue: #31
