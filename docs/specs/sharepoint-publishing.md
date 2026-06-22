# SharePoint Publishing Specification

## Status

Proposed

## Purpose

この Spec は、SPAutoPost が社内 SharePoint お知らせ掲示板へセキュリティ情報を掲載する際の投稿方式、権限、状態、失敗時動作、監査要件を定義します。

## Scope

対象:

- 投稿先 SharePoint site の指定
- お知らせ掲示板の実体確認
- SharePoint List item と Site Page の選定
- Microsoft Graph 権限
- 下書き、公開、更新、失敗時動作
- 投稿結果の記録
- 冪等性と重複投稿防止

非対象:

- 本番 tenant の Secret 登録
- 複数 SharePoint site への同時投稿
- 複雑な page layout / web parts 設計
- 社外公開サイトへの投稿

## Publishing Mode

初期候補は次の 2 つです。

### Option A: SharePoint List item

お知らせ掲示板が SharePoint List として運用されている場合に採用します。

想定用途:

- 既存掲示板が list item ベース
- 件名、本文、カテゴリ、重要度、掲載期間などが列で管理されている
- 投稿後の一覧性と検索性を優先する

確認事項:

- list ID
- required fields
- field internal names
- attachment の要否
- approval flow の有無
- versioning の有無

### Option B: SharePoint Site Page

お知らせ掲示板が Site Page / News page として運用されている場合に採用します。

想定用途:

- 既存掲示板がニュースページ形式
- リッチな本文、リンク、画像、セクション構成が必要
- SharePoint の標準ニュース表示と連携したい

確認事項:

- page library
- draft / publish の扱い
- page layout
- title area
- content web part
- approval flow の有無

## Decision Rule

初期実装では、既存のお知らせ掲示板の実体に合わせます。

判断順:

1. 既存掲示板が List の場合は List item を優先する。
2. 既存掲示板が Site Page / News の場合は Site Page を優先する。
3. どちらでも実現できる場合は、権限最小化、下書き運用、既存 UI との整合、運用担当者の編集容易性で比較する。
4. 判断結果は decision record に残す。

## Configuration

投稿先は設定で固定します。任意 URL への投稿は許可しません。

推奨設定項目:

```yaml
sharepoint:
  mode: list-item # list-item | site-page
  tenant_id: env:SPAUTOPOST_TENANT_ID
  site_id: env:SPAUTOPOST_SHAREPOINT_SITE_ID
  list_id: env:SPAUTOPOST_SHAREPOINT_LIST_ID
  page_library_id: env:SPAUTOPOST_SHAREPOINT_PAGE_LIBRARY_ID
  default_draft: true
  allow_publish: false
  idempotency_scope: site-and-list
```

## Permissions

Microsoft Graph 権限は最小権限とします。

設計方針:

- 読み取りだけで足りる source 確認と、投稿用権限を分離する。
- 本番運用では専用 app registration または managed identity を使う。
- 広すぎる権限は避け、投稿対象 site / list に限定できる方式を優先する。
- delegated permission と application permission のどちらを使うかは運用方式に応じて Issue で確定する。

## Draft and Publish Policy

MVP では、直接公開を既定値にしません。

- default: draft または test posting
- production publish: explicit approval required
- approved でない DraftPost は publish 不可
- dry-run では Graph API による作成・更新を行わない

## Idempotency

重複投稿を防ぐため、Publication は idempotency_key を持ちます。

推奨生成要素:

- draft_id
- target_site_id
- target_list_id または target_page_library_id
- advisory_ids
- normalized title hash

再実行時の動作:

1. idempotency_key が既存 Publication に存在するか確認する。
2. published / publishing の場合は新規作成しない。
3. failed の場合は retry policy に従う。
4. 既存 SharePoint item/page ID がある場合は update 候補として扱う。

## Error Handling

代表的な失敗:

- authentication_failed
- authorization_failed
- target_not_found
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
- target site/list/page
- operation: dry-run / create / update / publish
- actor or service principal
- approval status
- idempotency_key
- SharePoint item/page ID
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

- 既存お知らせ掲示板の実体は List item か Site Page か。
- 承認後に SPAutoPost が公開まで行うか、SharePoint 側の承認フローに渡すだけか。
- Delegated permission と application permission のどちらを使うか。
- 添付ファイルや画像を初期対象に含めるか。

## Related Issues

- #2 Confirm SharePoint announcement board contract
- #9 Implement SharePoint connector proof-of-concept
- #20 Implement SharePoint publish idempotency and state tracking
