# SharePoint List Item vs Site Page

## Status

Proposed

## Context

SPAutoPost は社内 SharePoint お知らせ掲示板へセキュリティ情報を掲載します。投稿方式として、SharePoint List item と SharePoint Site Page の 2 方式が候補です。

## Decision

未決定。

初期 Issue #2 で、既存のお知らせ掲示板の実体、既存 UI、承認フロー、必要な Microsoft Graph 権限、運用担当者の編集容易性を確認して決定します。

## Options

### Option A: List item

採用条件:

- 既存掲示板が List として運用されている
- 件名、本文、カテゴリ、重要度、掲載期間などを列で管理している
- 一覧性と検索性を優先する

### Option B: Site Page

採用条件:

- 既存掲示板が SharePoint News / Site Page として運用されている
- リッチな本文構成やニュース表示と連携したい
- page lifecycle と publish flow を使いたい

## Consequences

List item を選ぶ場合:

- field schema の確定が重要
- list permission と item lifecycle を設計する
- シンプルな投稿がしやすい

Site Page を選ぶ場合:

- page layout と publish lifecycle の設計が重要
- Graph API payload が複雑になりやすい
- 標準ニュース表示との整合を取りやすい

## Related

- Issue: #2
- Spec: docs/specs/sharepoint-publishing.md
