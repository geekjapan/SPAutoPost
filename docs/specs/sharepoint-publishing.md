# SharePoint Publishing Specification

## Status

Accepted for MVP publishing mode. Proposed for authentication and production publish details.

## Purpose

この Spec は、SPAutoPost が社内 SharePoint お知らせ掲示板へセキュリティ情報を掲載する際の投稿方式、権限、状態、失敗時動作、監査要件を定義します。

## MVP Decision

MVP の SharePoint 投稿対象は、SharePoint Site Page / News article 形式とします。

SPAutoPost は、脆弱性情報やセキュリティ対策情報を記事・ニュース形式で詳細に掲載するため、MVP では SharePoint List item ではなく Site Page / News を主経路とします。

## Scope

対象:

- 投稿先 SharePoint site の指定
- SharePoint Site Page / News article 投稿
- Microsoft Graph 権限
- 下書き、公開、更新、失敗時動作
- 投稿結果の記録
- 冪等性と重複投稿防止

非対象:

- 本番 tenant の Secret 登録
- 複数 SharePoint site への同時投稿
- 複雑な page layout / web parts 設計
- 社外公開サイトへの投稿
- SharePoint List item を主経路とする投稿

## Publishing Mode

### Selected: SharePoint Site Page / News article

採用理由:

- 既存のお知らせ掲示板が SharePoint Site Page / News 形式である
- 脆弱性情報の詳細、対応方法、参考リンクを記事形式で掲載しやすい
- SharePoint の標準ニュース表示と整合しやすい
- 一般利用者向け説明と管理者向け補足を同一記事内で整理しやすい

確認事項:

- page library
- draft / publish の扱い
- page layout
- title area
- content web part
- approval flow の有無
- News としての publish / promote の扱い

### Not Selected for MVP: SharePoint List item

List item 方式は MVP の主経路ではありません。

将来、一覧管理、ワークフロー管理、内部状態管理のために補助的な SharePoint List を使う可能性はあります。ただし掲示板本文の掲載先としては Site Page / News を優先します。

## Configuration

投稿先は設定で固定します。任意 URL への投稿は許可しません。

推奨設定項目:

```yaml
sharepoint:
  mode: site-page
  tenant_id: env:SPAUTOPOST_TENANT_ID
  site_id: env:SPAUTOPOST_SHAREPOINT_SITE_ID
  page_library_id: env:SPAUTOPOST_SHAREPOINT_PAGE_LIBRARY_ID
  default_draft: true
  allow_publish: false
  idempotency_scope: site-and-page-library
```

## Permissions

Microsoft Graph 権限は最小権限とします。

設計方針:

- 読み取りだけで足りる source 確認と、投稿用権限を分離する。
- 本番運用では専用 app registration または managed identity を使う。
- 広すぎる権限は避け、投稿対象 site / page library に限定できる方式を優先する。
- delegated permission と application permission のどちらを使うかは MVP 実装前に確定する。

## Draft and Publish Policy

MVP では、直接公開を既定値にしません。

- default: draft または test posting
- production publish: explicit approval required
- approved でない DraftPost は publish 不可
- dry-run では Graph API による作成・更新を行わない

## Site Page Content Model

MVP の記事構成は `docs/specs/draft-composition.md` に従います。

必須セクション:

1. 件名
2. 概要
3. 影響
4. 対象
5. 利用者が行う対応
6. 管理者が行う対応
7. 対応期限または推奨対応時期
8. 参考情報

## Idempotency

重複投稿を防ぐため、Publication は idempotency_key を持ちます。

推奨生成要素:

- draft_id
- target_site_id
- target_page_library_id
- advisory_ids
- normalized title hash

再実行時の動作:

1. idempotency_key が既存 Publication に存在するか確認する。
2. published / publishing の場合は新規作成しない。
3. failed の場合は retry policy に従う。
4. 既存 SharePoint page ID がある場合は update 候補として扱う。

## Error Handling

代表的な失敗:

- authentication_failed
- authorization_failed
- target_not_found
- page_library_not_found
- required_field_missing
- graph_rate_limited
- graph_timeout
- duplicate_detected
- publish_rejected

失敗時は、Publication.error_code / error_message / retryable を記録します。

## Audit Requirements

記録する項目:

- draft_id
- advisory_ids
- target site/page library/page
- operation: dry-run / create / update / publish
- actor or service principal
- approval status
- idempotency_key
- SharePoint page ID
- result
- error code
- timestamp

ログに出してはいけない項目:

- access token
- refresh token
- client secret
- certificate private key
- authorization header
- cookie

## Open Questions

- 承認後に SPAutoPost が公開まで行うか、SharePoint 側の承認フローに渡すだけか。
- Delegated permission と application permission のどちらを使うか。
- 添付ファイルや画像を初期対象に含めるか。
- News としての publish / promote 操作を MVP に含めるか。

## Related Issues

- #2 Confirm SharePoint announcement board contract
- #9 Implement SharePoint connector proof-of-concept
- #20 Implement SharePoint publish idempotency and state tracking
