# SharePoint Publishing Specification

## Status

Accepted for MVP publishing mode and M1 dedicated SharePoint publishing.

## Purpose

この Spec は、SPAutoPost が社内 SharePoint お知らせ掲示板へセキュリティ情報を掲載する際の投稿方式、権限、状態、失敗時動作、監査要件を定義します。

## MVP Decision

MVP の SharePoint 投稿対象は、SharePoint Site Page / News article 形式とします。

SPAutoPost は、脆弱性情報やセキュリティ対策情報を記事・ニュース形式で詳細に掲載するため、MVP では SharePoint List item ではなく Site Page / News を主経路とします。

M1 では、専用 SharePoint site への投稿を許可します。管理者が Admin UI/API で記事を確認・修正・確定した後、SharePoint Site Page / News として投稿できます。

人間確認なしの自動投稿は M1 対象外です。

## Scope

対象:

- 投稿先 SharePoint site の指定
- SharePoint Site Page / News article 投稿
- Microsoft Graph 権限
- 下書き、更新、失敗時動作
- 投稿結果の記録
- 冪等性と重複投稿防止

非対象:

- 複数 SharePoint site への同時投稿
- 複雑な page layout / web parts 設計
- 社外公開サイトへの投稿
- SharePoint List item を主経路とする投稿
- 人間確認なしの自動投稿
- SPAutoPost からの直接公開（M1 では下書き作成のみ）
- News promote（`PromoteNewsArticle` 相当）の M1 実装
- 添付ファイル・画像の投稿（M1 では本文テキストのみ）

## Publishing Mode

### Selected: SharePoint Site Page / News article

採用理由:

- 既存のお知らせ掲示板が SharePoint Site Page / News 形式である
- 脆弱性情報の詳細、対応方法、参考リンクを記事形式で掲載しやすい
- SharePoint の標準ニュース表示と整合しやすい
- 一般利用者向け説明と管理者向け補足を同一記事内で整理しやすい

### Not Selected for MVP: SharePoint List item

List item 方式は MVP の主経路ではありません。

将来、一覧管理、ワークフロー管理、内部状態管理のために補助的な SharePoint List を使う可能性はあります。ただし掲示板本文の掲載先としては Site Page / News を優先します。

## Configuration

投稿先は設定で固定します。任意 URL への投稿は許可しません。

設定項目:

```yaml
sharepoint:
  mode: site-page                                                   # 必須: "site-page" 固定
  tenant_id: env:SPAUTOPOST_TENANT_ID                               # 必須
  site_id: env:SPAUTOPOST_SHAREPOINT_SITE_ID                        # 必須
  page_library_id: env:SPAUTOPOST_SHAREPOINT_PAGE_LIBRARY_ID        # 必須
  dedicated_site: true                                              # 必須: 専用サイトのみ許可
  default_draft: true                                               # 必須: デフォルトは下書き
  allow_publish: false                                              # M1: SPAutoPost からの直接公開は行わない
  news_promote: false                                               # M1: News promote は非対象
  idempotency_scope: site-and-page-library                          # 必須
security:
  require_approval: true                                            # 必須: 管理者承認後のみ投稿可
```

`tenant_id`、`site_id`、`page_library_id` のいずれかが未設定の場合、アプリケーションは起動時バリデーションエラーを返します。

## Permissions

Microsoft Graph 権限は最小権限とします。

### Azure hosted runtime（application permission / managed identity）

推奨構成:

| Permission | 用途 | 種別 |
|---|---|---|
| `Sites.ReadWrite.All` | Site Page 作成の文書化された最小権限（`POST /sites/{siteId}/pages`） | Application |
| `Sites.Selected` | サイト限定アクセス（推奨候補・要検証。site page 操作での動作は #27 で確認） | Application |

`Sites.ReadWrite.All` が Graph v1.0 ドキュメントで明示されている最小権限。`Sites.Selected` はサイト限定アクセスとして推奨候補だが、site page 操作（`POST /sites/{siteId}/pages`）での動作確認は #27 に委ねる（未検証）。本番確定まで `Sites.ReadWrite.All` を使用する。`Files.ReadWrite.All` は M1 では不要（添付・画像は M1 非対象）。

### ローカル PoC（delegated permission）

| Permission | 用途 |
|---|---|
| `Sites.ReadWrite.All` | 対話型認証でのローカル検証 |

### 権限設計方針

- 読み取りだけで足りる source 確認と、投稿用権限を分離する。
- Azure hosted runtime では user-assigned managed identity を第一候補とする。
- ローカル PoC では delegated permission を許容する。
- SPAutoPost はこれら以外の Graph 権限を要求しない。
- 広すぎる権限を避け、投稿対象 site / page library に限定できる方式を優先する。本番環境では `Sites.ReadWrite.All` から `Sites.Selected` へ移行を完了させること。暫定使用は PoC と初期セットアップ期間に限る。

## Draft and Publish Policy

M1 では、SPAutoPost は SharePoint Site Page を下書き（`draft`）状態で作成します。

### ライフサイクル

```text
pending → publishing → published（下書きページ作成完了、SharePoint 上では未公開）
         ↘ dry_run                ↘ failed
         ↘ skipped（冪等性により作成省略）
```

| 状態 | 説明 |
|---|---|
| `pending` | 投稿キュー待機中 |
| `publishing` | Graph API 呼び出し中 |
| `published` | 下書きページの**作成成功**。**SharePoint 上では未公開（下書き）** — 状態名は Publication の処理完了を意味し、SharePoint 上の公開状態ではない |
| `dry_run` | dry-run モードで実行された（SharePoint への作成・更新は行われていない） |
| `skipped` | 冪等性チェックにより既存の Publication が検出され、作成をスキップした |
| `failed` | エラー発生 |

### M1 の公開方針

- SPAutoPost は Graph API publish エンドポイント（`/sites/{siteId}/pages/{pageId}/microsoft.graph.sitePage/publish`）を M1 では呼び出しません。
- 公開は SharePoint 画面から管理者が手動で行うか、SharePoint 側の承認フローに委ねます。
- `news_promote: false` が設定されている場合、News promote エンドポイントは呼び出されません。
- ログに `publish skipped (M1)` が記録されます。
- 公開範囲は対象 SharePoint サイトの既存アクセス権設定に従います。SPAutoPost の設定前に、管理者は対象サイトのアクセス権が意図したスコープ（組織内限定など）に設定されていることを確認しなければなりません（本 Spec が扱うのは CVE / セキュリティ勧告等の機微情報のため）。

### 投稿条件

- generated DraftPost はそのまま投稿しない。
- Admin UI/API で管理者が確認・修正・確定する。
- `approved` または `publish_requested` でない DraftPost は投稿不可。
- dry-run では SharePoint への作成・更新を行わない。
- 投稿結果は Publication と AuditEvent に記録する。

## Site Page Content Model

MVP の記事構成は `docs/specs/draft-composition.md` に従います。

M1 では本文テキストのみ投稿対象とします（添付ファイル・画像は M1 非対象）。

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
2. `published` / `publishing` の場合は新規作成しない。
3. `failed` の場合は retry policy に従う。
4. 既存 SharePoint page ID がある場合は update 候補として扱う。

## Error Handling

代表的な失敗とその retryable フラグ:

| error_code | 説明 | retryable |
|---|---|---|
| `authentication_failed` | 認証失敗（401） | false |
| `authorization_failed` | 権限不足（403） | false |
| `target_not_found` | 投稿先サイトが見つからない | false |
| `page_library_not_found` | page library が見つからない | false |
| `required_field_missing` | 必須フィールド欠落 | false |
| `graph_rate_limited` | Graph API レート制限（429） | true（exponential backoff） |
| `graph_timeout` | Graph API タイムアウト | true |
| `duplicate_detected` | idempotency_key 重複（`skipped` 状態へ遷移） | false |

失敗時は、`Publication.error_code` / `error_message` / `retryable` を記録します。

## Audit Requirements

記録する項目:

- draft_id
- advisory_ids
- target site / page library / page
- operation: dry-run / create / update
- approver
- publisher identity
- approval status
- idempotency_key
- SharePoint page ID
- result
- error code
- timestamp

## Related Issues

- #2 Confirm SharePoint announcement board contract
- #9 Implement SharePoint connector proof-of-concept
- #20 Implement SharePoint publish idempotency and state tracking
