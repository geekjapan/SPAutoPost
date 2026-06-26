## Context

`docs/specs/sharepoint-publishing.md` は MVP の投稿方式（Site Page / News article）を決定しているが、以下が未確定のまま Open Questions として残っていた。

- News promote（`PromoteNewsArticle`）を M1 に含めるか
- 承認後に SPAutoPost が公開まで行うか、SharePoint 側の承認フローに渡すだけか
- delegated / application permission / managed identity のどれを MVP で使うか
- 添付ファイルや画像を M1 対象に含めるか
- 専用 SharePoint site での公開範囲

本 change は実装ではなく、これらを Spec として確定して Issue #2 の受け入れ条件を満たす。

## Goals / Non-Goals

**Goals:**

- Graph 権限セットを最小権限で明示的に列挙する
- 下書き/公開/更新/削除のライフサイクルを確定する
- News promote を M1 スコープに含めるか否かを決定する
- 投稿先設定項目の完全な定義を確定する
- Open Questions をすべて解決して Spec に反映する

**Non-Goals:**

- 実装コードの作成・変更
- SharePoint Connector の PoC（Issue #9）
- 複数サイト対応
- 添付ファイル・画像の M1 実装

## Decisions

### D1: News promote を M1 スコープに含めない

**決定**: M1 では Site Page を下書き状態で作成し、管理者が SharePoint 画面から公開する。`PromoteNewsArticle` API（`/pages/{id}/microsoft.graph.sitePage/publish`）を SPAutoPost から呼ぶのは M1 外。

**理由**: M1 の人間確認ゲートを優先し、自動公開は最小限に抑える。News promote は M2 以降の候補とする。

**代替案**: SPAutoPost が publish まで行う → 管理者の最終確認なしに公開される可能性があり M1 のポリシーと矛盾する。

### D2: Graph 権限は application permission（managed identity）を優先

**決定**:
- Azure hosted runtime: user-assigned managed identity（application permission）
- ローカル PoC: delegated permission（`Sites.ReadWrite.All` を暫定）

**理由**: M1 は Azure Container Apps 上での運用が前提であり、managed identity が最小権限・無秘密での運用に適する。

**最小権限セット（application permission）**:
- `Sites.Selected`（推奨）または `Sites.ReadWrite.All`（暫定）
- `Files.ReadWrite.All`（page library への書き込みに必要な場合）

### D3: 公開範囲は SharePoint site のアクセス設定に委ねる

**決定**: SPAutoPost は page のアクセス権を変更しない。公開範囲は投稿先 SharePoint site の既存アクセス権設定に従う。

**理由**: SPAutoPost の責務はコンテンツ投稿であり、権限管理は SharePoint 管理者の責務。

### D4: 添付ファイル・画像は M1 非対象

**決定**: M1 では本文テキスト（Adaptive Card text body）のみ投稿対象。添付・画像は M1 スコープ外。

**理由**: Graph API での DriveItem 操作と page content の組み合わせは複雑度が高く、M1 の最小スコープに収まらない。

### D5: 下書き作成後の承認フロー

**決定**: SPAutoPost は SharePoint 上に下書き（`draft` 状態）として page を作成する。SharePoint 側の承認フローが有効な場合はそちらに渡す。SPAutoPost は公開完了のポーリングを行わない（M1 では非同期確認不要）。

## Risks / Trade-offs

- `Sites.Selected` は個別 site への付与設定が必要で初期セットアップが煩雑 → セットアップ手順を Spec に明記して対処
- Graph API の page 作成 payload（`/sites/{siteId}/pages`）は beta endpoint の可能性があり変更リスクあり → M1 実装時に v1.0 vs beta を再確認（Issue #9 で対処）
- 下書き作成後の公開が人手に委ねられるため、投稿完了の自動検知は M1 では行わない → 運用上の注意事項として Spec に記載

## Open Questions

（本 change で全件解消予定）

- [解消] News promote → M1 非対象（D1）
- [解消] 承認後 publish → SharePoint 側承認フロー委任（D5）
- [解消] 権限方式 → managed identity / application permission 優先（D2）
- [解消] 添付・画像 → M1 非対象（D4）
- [解消] 公開範囲 → SharePoint site 設定に委任（D3）
