## ADDED Requirements

### Requirement: Firecrawl adapter は URL から Markdown を取得する
Firecrawl adapter は `SourceAdapter` インターフェースを実装し、入力 URL を `firecrawl-py` SDK 経由で Firecrawl API に送信して Markdown テキストと metadata を取得しなければならない（MUST）。
取得結果は `SourceDocument`（`SourceRecord` + `raw_payload`）として返さなければならない（SHALL）。
`FIRECRAWL_API_KEY` 環境変数が未設定の場合は `validate_config()` が失敗ステータスを返さなければならない（MUST）。

#### Scenario: API key が設定されており URL が取得可能な場合
- **WHEN** `validate_config()` を呼び出し `FIRECRAWL_API_KEY` が設定されている
- **THEN** `AdapterStatus(ok=True)` を返す

#### Scenario: API key が未設定の場合
- **WHEN** `validate_config()` を呼び出し `FIRECRAWL_API_KEY` が未設定
- **THEN** `AdapterStatus(ok=False, code="missing_api_key")` を返す

#### Scenario: 有効な URL を fetch した場合
- **WHEN** `fetch(query)` に有効な URL を含む `SourceFetchQuery`（url フィールド）を渡す
- **THEN** `SourceDocument` のリスト（1件）を返す
- **THEN** `SourceRecord.source_type` は `"web_scrape"` である
- **THEN** `SourceRecord.source_url` は入力 URL と一致する
- **THEN** `raw_payload["markdown"]` に取得した Markdown テキストが含まれる
- **THEN** `raw_payload["metadata"]` に Firecrawl が返す metadata が含まれる

#### Scenario: Firecrawl API がエラーを返した場合
- **WHEN** Firecrawl API が HTTP エラー（4xx/5xx）を返す
- **THEN** `SourceAdapterError` を送出する

### Requirement: Firecrawl adapter は SourceDocument を Advisory に正規化する
`normalize(document)` は raw_payload の markdown・metadata.title・metadata.sourceURL を Advisory の各フィールドに写像しなければならない（MUST）。
LLM 変換は行わず、直接 field 写像のみ実施しなければならない（SHALL）。

#### Scenario: Markdown と metadata が揃っている場合
- **WHEN** `normalize(document)` を呼び出し `raw_payload` に `markdown` と `metadata.title`・`metadata.sourceURL` が含まれる
- **THEN** `Advisory.title` は `metadata.title` の値である
- **THEN** `Advisory.summary` は Markdown テキスト（先頭 500 文字）である
- **THEN** `Advisory.references` に `{"label": "Source", "url": source_url, "type": "web_scrape"}` が含まれる
- **THEN** `Advisory.severity` は `"unknown"` である
- **THEN** `Advisory.tags` に `"firecrawl"` が含まれる

#### Scenario: metadata.title が取得できない場合
- **WHEN** `normalize(document)` を呼び出し `raw_payload["metadata"]["title"]` が空または未設定
- **THEN** `Advisory.title` は入力 URL の文字列を使用する

### Requirement: Firecrawl adapter の spike 評価レポートを docs に作成する
spike 評価の結果として、`docs/spikes/firecrawl-adapter-spike.md` を作成し（SHALL）、
以下の情報をすべて記載しなければならない（MUST）。

#### Scenario: 評価レポートが作成される
- **WHEN** spike 評価を完了する
- **THEN** `docs/spikes/firecrawl-adapter-spike.md` が存在する
- **THEN** レポートに「取得結果サンプル」「Advisory 変換可否」「利用条件・コスト概算」「採否判断と根拠」が含まれる

### Requirement: Firecrawl adapter の設定は環境変数で管理する
Firecrawl adapter の設定値（API key・タイムアウト・最大取得文字数）は環境変数または config.yml で管理しなければならない（MUST）。
コードにハードコードしてはならない（SHALL NOT）。

#### Scenario: 設定値が環境変数から読み込まれる
- **WHEN** `FIRECRAWL_API_KEY` 環境変数が設定されている
- **THEN** adapter は API key を環境変数から取得する
- **THEN** コード内に API key の値が含まれない
