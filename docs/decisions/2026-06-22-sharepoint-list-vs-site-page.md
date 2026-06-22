# SharePoint List Item vs Site Page

## Status

Accepted

## Context

SPAutoPost は社内 SharePoint お知らせ掲示板へセキュリティ情報を掲載します。投稿方式として、SharePoint List item と SharePoint Site Page / News article の 2 方式が候補でした。

既存のお知らせ掲示板は SharePoint Site Page / News 形式であり、SPAutoPost では脆弱性情報やセキュリティ対策の詳細情報を記事・ニュース形式で掲載します。

## Decision

MVP の SharePoint 投稿方式は、SharePoint Site Page / News article とします。

SharePoint List item は MVP の主経路にはしません。ただし、将来、内部状態管理、一覧管理、補助的なワークフロー管理のために List を使う可能性は残します。

## Rationale

- 既存のお知らせ掲示板の実体が Site Page / News 形式である。
- 脆弱性情報、影響、対象、利用者向け対応、管理者向け対応、参考リンクを記事形式で詳細に掲載しやすい。
- SharePoint の標準ニュース表示と整合しやすい。
- 一般利用者にも読みやすい告知形式を作りやすい。

## Consequences

- MVP の SharePoint publisher は Site Page / News article を主対象にする。
- `sharepoint.mode` の既定値は `site-page` とする。
- 投稿 payload、page layout、draft/publish lifecycle の設計が必要になる。
- Graph API の payload は List item より複雑になる可能性がある。
- List item 用の field schema 設計は MVP の主作業から外す。

## Open Follow-ups

- News としての publish / promote 操作を MVP に含めるか。
- 承認後に SPAutoPost が公開まで行うか、SharePoint 側の承認フローに渡すだけか。
- delegated permission / application permission / managed identity のどれを MVP で使うか。
- 添付ファイルや画像を MVP に含めるか。

## Related

- Issue: #2
- Issue: #9
- Issue: #20
- Spec: docs/specs/sharepoint-publishing.md
- Spec: docs/specs/architecture.md
