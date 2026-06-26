# Firecrawl Source Adapter — Spike 評価レポート

**Issue**: #34 M1/Spike — Evaluate Firecrawl source adapter  
**評価日**: 2026-06-26  
**評価者**: Claude worker (geekjapan/issue-34-firecrawl-spike)  
**ステータス**: 完了

---

## 1. 目的

Firecrawl を URL 指定型 source adapter として SPAutoPost に組み込む実現可能性を評価する。
評価軸は以下の 4 点。

1. Firecrawl API の動作と取得結果の品質
2. `SourceAdapter` インターフェースへの適合可否
3. Advisory への変換可否
4. 利用条件・コスト・リスク

---

## 2. Firecrawl API 概要

| 項目 | 内容 |
|------|------|
| SDK | `firecrawl-py` (v4.30.3 時点) |
| メインクラス | `V1FirecrawlApp` |
| スクレイプ API | `scrape_url(url, formats=["markdown"], timeout=30000)` |
| レスポンス型 | `V1ScrapeResponse` |
| 主要フィールド | `markdown`, `title`, `metadata.sourceURL`, `metadata.statusCode` |
| 認証 | API key（`FIRECRAWL_API_KEY` 環境変数） |

### 取得結果サンプル（構造）

```json
{
  "markdown": "# ページタイトル\n\n本文テキスト（Markdown 形式）...",
  "title": "ページタイトル",
  "metadata": {
    "title": "ページタイトル",
    "sourceURL": "https://example.com/advisory",
    "statusCode": 200,
    "description": "ページの説明文",
    "language": "ja"
  }
}
```

---

## 3. SourceAdapter インターフェース適合性

### 評価結果: ✅ 適合可能

| メソッド | 実装方法 | 評価 |
|----------|----------|------|
| `validate_config()` | `FIRECRAWL_API_KEY` の有無を検査 | ✅ 実装済み |
| `fetch(query)` | `query.url` を `scrape_url()` に渡す | ✅ 実装済み |
| `normalize(document)` | `markdown` → `summary`、`title` → `title`、`source_url` → `references` | ✅ 実装済み |

### 変更点

- `SourceFetchQuery` に `url: str | None` フィールドを追加（既存 adapter への影響なし）
- `SourceType` に `"web_scrape"` を追加（Literal 型の拡張 + `db/migrations/*/0002_add_web_scrape_source_type.sql` で DB 制約を更新）
- `FirecrawlSourceAdapter` を `src/spautopost/firecrawl_adapter.py` に新規実装

---

## 4. Advisory への変換可否

### 評価結果: ✅ 変換可能（ただし品質は LLM 連携なしでは限定的）

| Advisory フィールド | 変換元 | 変換品質 |
|--------------------|--------|----------|
| `title` | `metadata.title` または `url` | ✅ 高品質（ページタイトルそのまま） |
| `summary` | `markdown` 先頭 5000 文字 | ⚠️ 構造化されていない（本文全体を截断） |
| `references` | 入力 URL | ✅ 問題なし |
| `severity` | 固定値 `"unknown"` | ⚠️ 自動判定不可（LLM 連携が必要） |
| `cve_ids` | 変換不可（構造化抽出なし） | ❌ Markdown から CVE ID を抽出する処理が必要 |
| `affected_products` | 変換不可 | ❌ 同上 |

**改善余地**: LLM（Claude Haiku 等）を組み合わせれば Markdown テキストから severity・cve_ids・affected_products を抽出可能。ただしこれは M1 spike 対象外。

---

## 5. 利用条件・コスト・制約

### API key 取得

1. [firecrawl.dev](https://firecrawl.dev) でアカウント作成
2. Dashboard から API key（`fc-...` 形式）を取得
3. `FIRECRAWL_API_KEY` 環境変数に設定

### 料金プラン（2026-06 時点の概算）

| プラン | 月間クレジット | 参考コスト |
|--------|--------------|------------|
| Free | ~500 pages/月 | $0 |
| Hobby | ~3,000 pages/月 | ~$16/月 |
| Standard | ~100,000 pages/月 | ~$83/月 |

M1 の利用規模（数十 URL/日 程度）では Free または Hobby で十分。

### Rate limit

- Free プランは同時リクエスト数および月間 page 数の上限あり
- バースト的な取得（大量 URL を一括スクレイピング）は非推奨

### 利用規約上の注意

- スクレイピング対象サイトの利用規約を個別確認する義務がある
- robots.txt を遵守する設定（`only_main_content=True` 等）を推奨
- 対象サイトが CISA・JVN・NVD のような公的機関の場合、scraping より公式 API の利用を優先すること

### セキュリティ

- `FIRECRAWL_API_KEY` をコード・ログ・git に含めない
- 取得した Markdown は信頼しない（HTML injection の可能性）
- Draft Composition と Review を通じて内容をサニタイズする

---

## 6. テスト結果

```
tests/test_firecrawl_adapter.py .........  9 passed in 0.20s
```

- `validate_config()`: API key あり/なし ✅
- `normalize()`: title あり/なし、長文截断 ✅
- `fetch()`: mock による SourceDocument 検証、API エラー処理 ✅

---

## 7. 採否判断

### 判断: ✅ M1 に含める（optional）

**根拠:**

1. **実現可能**: `SourceAdapter` インターフェースへの適合は完全に実現可能であり、実装コストは低い
2. **即時利用可能**: `firecrawl-py` の SDK は安定しており、API key さえあれば即日利用開始できる
3. **M1 スコープに合致**: vendor advisory 等の構造化 API がないページを取り込む用途として有用
4. **コスト許容**: 数十 URL/日 規模では Free プランで間に合う
5. **限定的な品質は許容範囲**: M1 は人間レビューが前提のため、summary が構造化されていなくても Draft 生成の入力として使用可能

**条件:**

- Firecrawl adapter は M1 で `[project.optional-dependencies.spike]` として提供し、本番採用は M2 以降に昇格判断する
- severity・cve_ids の自動抽出は M2 以降の LLM 連携 Issue で扱う
- 対象 URL はオペレーター責任で利用規約を確認する運用ガイドを docs に追加する

### 保留事項（M2 以降）

- CVE ID・affected_products の Markdown からの自動抽出（LLM 連携）
- rate limit 超過時の backoff リトライ実装
- robots.txt 遵守の自動検査

---

## 8. 参照

- `src/spautopost/firecrawl_adapter.py` — adapter 実装
- `samples/firecrawl_spike.py` — 動作確認スクリプト
- `tests/test_firecrawl_adapter.py` — テスト
- `docs/specs/source-collection.md` — Firecrawl adapter セクション
- [Firecrawl 公式ドキュメント](https://docs.firecrawl.dev)
