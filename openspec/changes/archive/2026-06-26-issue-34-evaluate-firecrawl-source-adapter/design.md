## Context

SPAutoPost は既存の NVD・KEV・Vendor Advisory 等の構造化ソースを `SourceAdapter` インターフェース経由で取得している。
Firecrawl は URL を指定すると Markdown に変換して返す外部 API であり、任意の Web ページを情報源として扱えるため、
構造化 API のない vendor advisory や blog 記事を取り込む用途として評価価値がある。
本 spike は M1 optional として位置づけられており、成果物はドキュメント（評価レポート・spec 更新）と検証スクリプトにとどめる。

## Goals / Non-Goals

**Goals:**
- Firecrawl API の動作（URL → Markdown 取得）を実機で確認する
- `SourceAdapter` インターフェースへの適合可能性を評価する（fetch / normalize フロー）
- Markdown → Advisory 変換の実現可否と品質を試験する
- 利用条件（API key 管理・rate limit・コスト・利用規約）を整理する
- M1 採用 / M2 以降送り の採否判断根拠をドキュメント化する

**Non-Goals:**
- 本番 adapter の実装（spike のみ）
- 大量 URL の取得・クロール
- 高精度な Advisory 正規化（LLM 連携含む）
- Firecrawl 以外の scraping サービスとの比較評価

## Decisions

### D1: spike 出力形式

**決定**: 評価レポート（`docs/spikes/firecrawl-adapter-spike.md`）+ `docs/specs/source-collection.md` への追記  
**理由**: 本番コードを追加せず spec を更新するだけで採否判断ができる。コードが必要な検証は scratchpad スクリプトで行い、リポジトリには含めない（または `samples/` に限定する）。  
**代替案**: spike ブランチに試験実装を置く → 後始末が必要で M1 スコープを汚染するため却下。

### D2: Firecrawl 呼び出し方法

**決定**: `firecrawl-py` SDK を使用（`pip install firecrawl-py`）  
**理由**: 公式 SDK で認証・retry・エラー処理が含まれており、raw HTTP より確認効率が高い。spike なので依存追加の影響は最小。  
**代替案**: `httpx` で直接 `/v1/scrape` を呼ぶ → 可能だが SDK で十分。

### D3: Advisory 変換方式

**決定**: Firecrawl が返す Markdown テキストを `summary` として扱い、`title` は `metadata.title`、`source_url` は入力 URL をそのまま使う  
**理由**: spike 段階では LLM による高精度抽出は不要。単純な field 写像で Advisory への変換が可能かを確認する。  
**代替案**: LLM で Markdown → Advisory field を抽出 → spike 評価としてはスコープ超過。

### D4: SourceType の扱い

**決定**: Firecrawl 取得は新規 `"web_scrape"` で表現する  
**理由**: `external_collector` は外部バッチ収集ジョブを指す既存値であり Firecrawl スクレイピングとは意味が異なる。`"web_scrape"` を新規追加することで意図を明確化する。`SourceType` Literal への追加 + `db/migrations/*/0002_add_web_scrape_source_type.sql` マイグレーションで DB CHECK 制約も更新済み。

## Risks / Trade-offs

| リスク | 緩和策 |
|--------|--------|
| Firecrawl API key がなく実機確認できない | `.env` 経由で提供、なければ mock レスポンスで構造確認にとどめる |
| Markdown 品質が Advisory 変換に不十分 | spike レポートに「変換可否: 不可」と記録して M2 以降に送る根拠とする |
| rate limit / コストが M1 予算外 | Firecrawl 無料プランの制限を確認し、コスト試算を spike レポートに含める |
| `SourceType` の enum 拡張が storage schema に影響 | spike 段階では型ヒントのみ提示し、本採用時に別 Issue で schema 変更を扱う |
| 利用規約上 scraping が制限されるサイトへの適用 | レポートに利用制限の注意事項を明記し、ユーザー責任を明確化する |
