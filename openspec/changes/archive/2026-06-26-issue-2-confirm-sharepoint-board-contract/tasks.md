## 1. Spec 更新

- [x] 1.1 `docs/specs/sharepoint-publishing.md` の Open Questions を解消し、確定内容を反映する
- [x] 1.2 Graph 権限セット（`Sites.Selected` / `Sites.ReadWrite.All` / `Files.ReadWrite.All`）を Permissions セクションに明示列挙する
- [x] 1.3 `allow_publish: false` / `news_promote: false` を Configuration セクションに追加する
- [x] 1.4 投稿ライフサイクル（`pending` → `publishing` → `published` / `failed`）を Draft and Publish Policy セクションに追記する
- [x] 1.5 エラーコードごとの retryable フラグを Error Handling セクションに明示する
- [x] 1.6 添付ファイル・画像は M1 非対象であることを Scope 非対象に追記する

## 2. 受け入れ条件チェック

- [x] 2.1 Site Page / News article 採用が Spec に明記されていること（Issue #2 AC: 1項目目）
- [x] 2.2 必要な Graph permission が整理されていること（Issue #2 AC: 2項目目）
- [x] 2.3 投稿先の設定項目が定義されていること（Issue #2 AC: 3項目目）
- [x] 2.4 下書き/公開/更新/失敗時動作が定義されていること（Issue #2 AC: 4項目目）
- [x] 2.5 `docs/specs/sharepoint-publishing.md` が更新されていること（Issue #2 AC: 5項目目）
