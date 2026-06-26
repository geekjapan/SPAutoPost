## ADDED Requirements

### Requirement: source-collection は Firecrawl adapter を外部 Web ページ取得手段として定義する
`SourceType` に `"web_scrape"` を追加しなければならない（SHALL）。Firecrawl adapter を URL 指定による外部 Web ページ取得用 adapter として位置付ける。
Firecrawl adapter は既存 `SourceAdapter` インターフェース（`validate_config` / `fetch` / `normalize`）を実装しなければならない（MUST）。

#### Scenario: Firecrawl adapter が SourceAdapter インターフェースを実装する
- **WHEN** Firecrawl adapter の `validate_config()` / `fetch()` / `normalize()` を呼び出す
- **THEN** 既存の `SourceAdapter` Protocol に適合する
- **THEN** `source_type` が `"web_scrape"` である

### Requirement: Firecrawl adapter の設定項目を source-collection spec に定義する
Firecrawl adapter が必要とする設定項目（FIRECRAWL_API_KEY 等）を source-collection spec に定義しなければならない（MUST）。
対象は API key・タイムアウト・最大取得文字数とする（SHALL）。

#### Scenario: Firecrawl adapter の設定項目が定義されている
- **WHEN** source-collection の設定を参照する
- **THEN** 以下の設定項目が定義されていることを確認できる：
  `FIRECRAWL_API_KEY`（必須）、`FIRECRAWL_TIMEOUT_SECONDS`（省略可・デフォルト 30）、
  `FIRECRAWL_MAX_CONTENT_CHARS`（省略可・デフォルト 5000）

### Requirement: Firecrawl adapter の利用条件と制限を source-collection spec に記載する
Firecrawl adapter の利用条件（前提条件・rate limit・コスト・利用規約上の注意事項）を source-collection spec に明記しなければならない（MUST）。
運用者が採否判断できる内容を含まなければならない（SHALL）。

#### Scenario: 利用条件が spec に記載されている
- **WHEN** source-collection spec の Firecrawl adapter セクションを参照する
- **THEN** API key 取得方法・無料プラン上限・コスト概算・スクレイピング対象サイトの利用規約確認義務が記載されている
