## Why

M1 の記事生成には十分な情報量が必要であり、URL 指定による Web ページ取得を手軽に実現できる Firecrawl を source adapter として採用可能か評価する。
個人検証での利用実績があるため、M1 optional spike として採否判断に必要な情報を整理する。

## What Changes

- Firecrawl を使った source adapter の spike 調査を実施し、実現可能性レポートを作成する
- URL 入力 → Markdown 取得 → Advisory 変換 → DraftPost 生成の各ステップの実現可否を検証する
- 評価結果に基づき、M1 に含めるか M2 以降に送るかの採否判断根拠を docs に記載する
- `docs/specs/source-collection.md` に Firecrawl adapter の利用条件・設定項目・制約を追記する

## Capabilities

### New Capabilities

- `firecrawl-source-adapter`: Firecrawl API を使った URL → Markdown 取得と Advisory 変換の spike 評価。input/output 仕様・設定項目・利用条件・採否判断根拠をドキュメント化する。

### Modified Capabilities

- `source-collection`: Firecrawl adapter の位置付け（外部 Web ページ取得用 adapter）と設定項目を source-collection spec に追記する。

## Impact

- `docs/specs/source-collection.md`: Firecrawl adapter セクションを追加
- `docs/` 以下: spike 評価レポート (`docs/spikes/firecrawl-adapter-spike.md`) を新規追加
- 依存ライブラリ: `firecrawl-py`（spike 評価のみ、本番採用は別途判断）
- Firecrawl API key が必要（環境変数 `FIRECRAWL_API_KEY`）
- 既存アーキテクチャへの破壊的変更なし（spike はドキュメントと試験コードのみ）
