## 1. 事前確認・環境準備

- [x] 1.1 Firecrawl 公式ドキュメントを確認し、API エンドポイント・レスポンス形式・rate limit・コスト体系を整理する
- [x] 1.2 `firecrawl-py` SDK を spike 用に `pyproject.toml` の `[project.optional-dependencies]` に追加する（`spike` グループ）
- [x] 1.3 `FIRECRAWL_API_KEY` 環境変数の取得方法を確認し、`.env.example` に記載する

## 2. Firecrawl API 動作確認（spike スクリプト）

- [x] 2.1 `samples/firecrawl_spike.py` に最小 spike スクリプトを作成し、URL → Markdown 取得の動作を確認する
- [x] 2.2 取得した Markdown と metadata（title・sourceURL）のサンプル出力をスクリプトで表示し、内容を記録する
- [x] 2.3 エラーケース（無効 URL・API key 未設定）の挙動を確認し、エラーメッセージを記録する

## 3. SourceAdapter インターフェース適合性の確認

- [x] 3.1 `SourceFetchQuery` に `url` フィールドを追加する（または `vendor`/`product` を流用する方法を評価する）
- [x] 3.2 `FirecrawlSourceAdapter` クラスのスケルトンを `source_adapters.py` に追加し、`SourceAdapter` Protocol に適合することを確認する
- [x] 3.3 `validate_config()` を実装し、`FIRECRAWL_API_KEY` の有無を検査する
- [x] 3.4 `fetch()` を実装し、`firecrawl-py` SDK で URL → `SourceDocument` を返すようにする
- [x] 3.5 `normalize()` を実装し、`raw_payload["markdown"]`・`raw_payload["metadata"]` → `Advisory` の field 写像を行う

## 4. テスト作成

- [x] 4.1 `validate_config()` の単体テストを作成する（API key あり・なし）
- [x] 4.2 `normalize()` の単体テストを作成する（Markdown + metadata あり・title なしのケース）
- [x] 4.3 `fetch()` を mock した統合テストを作成し、`SourceDocument` の内容を検証する

## 5. ドキュメント更新

- [x] 5.1 `docs/spikes/` ディレクトリを作成し、`firecrawl-adapter-spike.md` に評価レポートを作成する（取得結果サンプル・Advisory 変換可否・利用条件・コスト概算を含む）
- [x] 5.2 `docs/specs/source-collection.md` に Firecrawl adapter セクションを追記する（設定項目・利用条件・`SourceType: "web_scrape"` の定義）
- [x] 5.3 評価レポートに M1 採用 / M2 以降送りの採否判断と根拠を明記する

## 6. OpenSpec アーカイブと PR

- [x] 6.1 `openspec validate issue-34-evaluate-firecrawl-source-adapter --strict` を実行し、全項目パスすることを確認する
- [ ] 6.2 `opsx:archive` で change をアーカイブし、main specs を更新する
- [ ] 6.3 PR を作成する（base: main、タイトル: `feat(spike): evaluate Firecrawl source adapter (#34)`）
