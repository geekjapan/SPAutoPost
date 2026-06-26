# Spec: llm-provider

## Purpose

SPAutoPost が使用する LLM provider の interface 定義、M1/M3 スコープ宣言、および各 provider の利用条件・前提条件を規定する。mock provider (#6) を M1 必須とし、Azure OpenAI / Foundry・generic API は M3 以降とする。
## Requirements
### Requirement: Provider interface definition
Provider は以下の interface を実装しなければならない（SHALL）。この interface は M1 で確定版とし、mock provider (#6) の実装基準とする。

```text
Provider.validate_config() -> ProviderStatus
Provider.generate_draft(input: DraftInput) -> DraftOutput
Provider.get_provider_metadata() -> ProviderMetadata
Provider.estimate_cost(input: DraftInput) -> CostEstimate | None  # optional
```

`ProviderMetadata` には以下を含めること:
- `provider_name: str`
- `provider_type: "production_api" | "production_flow" | "generic_api" | "test_mock" | "test_manual"`
- `model: str | None`
- `prompt_version: str | None`

#### Scenario: mock provider が interface を実装する
- **WHEN** mock provider (#6) を実装する
- **THEN** `generate_draft`・`validate_config`・`get_provider_metadata` の 3 メソッドが実装されていること

#### Scenario: test_manual provider が interface を実装する
- **WHEN** test_manual 結果を DraftPost に手動取込する
- **THEN** `provider_type = "test_manual"` として audit log に記録されること

### Requirement: test_manual provider usage in M1
M1 において test_manual provider は手動取込フローのみで使用しなければならない（SHALL）。以下を禁止する:

- ChatGPT / Claude の UI 自動操作
- 非公式 API の利用
- 業務データ・社内限定情報の LLM への投入
- test_manual 結果の自動公開

手動取込フロー:
1. 担当者が ChatGPT / Claude subscription でサンプルデータを使い手動生成する
2. 生成結果を DraftPost として SPAutoPost に手動入力する
3. DraftPost の `provider_type` を `test_manual` に設定し audit log に記録する
4. レビュー・承認フローを経て SharePoint に投稿する

#### Scenario: test_manual 結果を DraftPost に手動取込する
- **WHEN** 担当者が LLM 手動生成結果を SPAutoPost に入力する
- **THEN** `provider_type = "test_manual"` が設定され、レビューなしに自動公開されないこと

#### Scenario: test_manual での業務データ投入を禁止する
- **WHEN** 担当者が test_manual フローを実施する
- **THEN** 業務データ・社内限定情報を ChatGPT / Claude に投入しないこと（運用ガイドに明記）

### Requirement: M1 scope declaration in spec
`docs/specs/llm-provider.md` は M1 スコープを明示しなければならない（SHALL）。

M1 必須:
- `test_mock` provider（mock provider #6）

M1 optional（手動のみ）:
- `test_manual` provider（手動取込フロー）

M3 以降:
- `production_api`（Azure OpenAI / Foundry — #16）
- `generic_api`（OpenAI-compatible — #17）
- `production_flow`（Copilot Studio — 別途検討）

#### Scenario: M1 に mock provider のみが必須として記録される
- **WHEN** `docs/specs/llm-provider.md` の M1 Scope セクションを確認する
- **THEN** `test_mock` が必須、`production_api` / `generic_api` が M3 以降として明記されていること

### Requirement: Azure OpenAI / Foundry M3 preconditions
Issue #16 (Azure OpenAI provider) の実装着手前に以下の前提条件を満たさなければならない（SHALL）:

- 入力データ許容範囲（社内 CVE 情報の投入可否）を情報セキュリティ部門が承認している
- 認証方式（Entra ID managed identity または API key）が確定している
- rate limit・失敗時動作・SLA が確認されている
- 監査ログ取得方法が確定している
- 利用契約・データ処理契約の業務利用可否が確認されている

#### Scenario: M3 着手前に前提条件を確認する
- **WHEN** Issue #16 (Azure OpenAI provider) の実装を開始する
- **THEN** 上記 5 点の前提条件が Issue #16 に記録・承認されていること

### Requirement: generic API M3 preconditions
Issue #17 (generic API provider) の実装着手前に以下の前提条件を満たさなければならない（SHALL）:

- 社内 CVE 情報等の入力データ許容範囲を情報セキュリティ部門が承認している
- 採用する vendor（OpenAI API / Anthropic API / 他）が決定されている
- 当該 vendor の利用条件・データ保持方針が業務利用上問題ないと確認されている
- OpenAI-compatible endpoint の adapter 設計が完了している
- 認証方式が確定している
- rate limit・失敗時動作・SLA が確認されている
- 監査ログ取得方法が確定している

#### Scenario: M3 着手前に generic API 前提条件を確認する
- **WHEN** Issue #17 (generic API provider) の実装を開始する
- **THEN** 上記 7 点の前提条件が Issue #17 に記録・承認されていること

### Requirement: production_api provider の利用条件
`production_api` provider（Microsoft Foundry / Azure OpenAI 等）を利用するシステムは、以下の条件を すべて 満たさなければならない（SHALL）。

1. API 利用が社内情報セキュリティ部門によって承認されている
2. 利用する API の規約上、業務データの投入が許可されている
3. Entra ID managed identity または組織が管理する API key で認証している
4. rate limit・タイムアウト・エラーハンドリングを実装している
5. 監査ログを取得または補完できる手段が確保されている

#### Scenario: production_api provider が未承認の状態で使用される
- **WHEN** `llm.production_approved` フラグが `true` でない状態で production_api provider を使用しようとする
- **THEN** システムは起動時設定バリデーションでエラーを返し、生成処理を開始してはならない

#### Scenario: production_api provider が適切に認証されている
- **WHEN** production_api provider が Entra ID managed identity で認証する
- **THEN** API key をコードまたは設定ファイルに直書きすることなく認証が完了すること

### Requirement: production_flow provider の利用条件
`production_flow` provider（Copilot Studio 等）を利用するシステムは、以下の条件をすべて満たさなければならない（SHALL）。

1. 入出力 schema が定義できる
2. 実行履歴または監査情報を追跡できる
3. SharePoint 投稿前の原稿生成用途に限定される
4. 失敗時に再試行または手動介入できる

#### Scenario: production_flow provider で生成失敗した場合
- **WHEN** Copilot Studio 等の flow 実行が失敗する
- **THEN** 自動リトライまたは担当者へのアラートを発し、サイレント無視してはならない

### Requirement: generic_api provider の利用条件
`generic_api` provider（OpenAI API / Anthropic API 等の OpenAI-compatible API）を利用するシステムは、以下の条件をすべて満たさなければならない（SHALL）。

1. endpoint / model / auth / request / response mapping を設定または adapter で分離している
2. 公式 API のみを使用し、非公式 API や UI scraping を使用しない
3. 採用 vendor の利用規約・データ保持方針が業務利用上問題ないと情報セキュリティ部門が確認している
4. 認証情報は環境変数または Secret store 経由でのみ参照する

#### Scenario: generic_api provider で非公式 API を使用しようとする
- **WHEN** generic_api provider の実装に非公式 API または UI scraping を含める
- **THEN** コードレビューでブロックし、実装を棄却しなければならない

### Requirement: test_mock provider の要件
`test_mock` provider を実装するシステムは、以下の要件をすべて満たさなければならない（SHALL）。

1. 外部ネットワーク通信を行わない
2. fixture から固定応答を返し、出力が決定的（deterministic）である
3. prompt version および input hash の検証に使用できる
4. CI 環境で Secret なしで動作する

#### Scenario: CI 環境で test_mock provider が動作する
- **WHEN** CI パイプラインが test_mock provider を使用するテストを実行する
- **THEN** 外部 API キーや環境変数なしにすべてのテストが通過すること

#### Scenario: test_mock provider が決定的な出力を返す
- **WHEN** 同一の DraftInput で test_mock provider を複数回呼び出す
- **THEN** 毎回同一の DraftOutput が返ること

### Requirement: test_manual provider の禁止事項
`test_manual` provider（ChatGPT / Claude subscription 等）の利用においては、以下を絶対に行ってはならない（MUST NOT）。

1. ブラウザ自動操作、Selenium、Playwright 等による UI 自動化
2. 非公式 API、reverse-engineered endpoint の利用
3. 業務データ（実 CVE 詳細、社内ネットワーク構成、未公開インシデント情報等）の LLM への投入
4. レビュー・承認フローを経ずに生成結果を SharePoint へ直接公開
5. `provider_type` を記録せずに DraftPost を生成すること

#### Scenario: test_manual で業務データを投入しようとする
- **WHEN** 担当者が test_manual フローで実 CVE 詳細や社内構成情報を ChatGPT / Claude に貼り付ける
- **THEN** 運用ガイドの禁止事項に違反したとして、審査・記録が必要になること

#### Scenario: test_manual 結果を自動公開しようとする
- **WHEN** システムが test_manual の DraftPost をレビューなしに SharePoint へ公開しようとする
- **THEN** publish フローが `provider_type = "test_manual"` を検出し、自動公開をブロックしなければならない

### Requirement: ChatGPT / Claude subscription を自動化前提にしない
ChatGPT / Claude subscription（Web UI: chat.openai.com / claude.ai のチャット画面）は実稼働自動化 provider として扱ってはならない（MUST NOT）。

用語の明確化:
- **ChatGPT subscription**: chat.openai.com の Web UI を人間が手動操作するサービス。test_manual 扱い。
- **OpenAI API**: api.openai.com の公式 REST API（プログラム呼び出し）。generic_api として扱い、利用条件確認が必要。
- **Claude subscription**: claude.ai の Web UI を人間が手動操作するサービス。test_manual 扱い。
- **Anthropic API**: api.anthropic.com の公式 REST API（プログラム呼び出し）。generic_api として扱い、利用条件確認が必要。

ChatGPT / Claude subscription（Web UI）に関する方針:
- 本 provider の利用は test_manual 分類に限定される
- 自動化・スケジュール実行・batch 処理の用途に使用しない
- 本 provider で生成した結果を経由して別の自動化フローをトリガーしない

#### Scenario: ChatGPT subscription を自動化 provider として登録しようとする
- **WHEN** 設定ファイルに `llm.provider = "production_api"` で ChatGPT subscription endpoint を登録する
- **THEN** システムの設定バリデーションがエラーを返し、起動を拒否しなければならない

### Requirement: provider へ渡してよい情報の定義
LLM provider（production_api / generic_api / test_manual すべてに適用）に渡す入力は最小化しなければならない（SHALL）。

渡してよい情報（許可リスト）:
- 公開された脆弱性情報（CVE / JVN / vendor advisory の要約）
- 一般公開されている参考 URL
- 一般化された社内向け文体指示・フォーマット指定
- 明示的に情報セキュリティ部門が許可した製品名またはカテゴリ
- urgency / target_audience / target_language 等のメタデータ
- prompt_version / template_id 等の制御パラメータ

渡してはならない情報（禁止リスト）:
- API key / access token / client secret / authorization header
- 個人識別情報（PII: 氏名・メールアドレス・社員番号等）
- 社内ネットワーク構成（内部 IP / hostname / VLAN / サブネット等）
- 認証方式の詳細（LDAP 構成、AD OU 構造、MFA 設定等）
- 未公開インシデント情報（報告前の社内セキュリティ障害等）
- 攻撃者に有益な内部防御状況（EDR 製品名・設定・検知ルール詳細等）
- 社内限定の詳細構成情報（例: 非公開の GitHub リポジトリ URL、内部 wiki hostname、承認なし製品名等）
- 攻撃手順・PoC 詳細・脆弱性の悪用手法（生成抑制のためプロンプトに含めない）

補足: `Advisory` 型および `Reference` 型が含めてよい情報の範囲は `docs/specs/data-model.md` を参照すること。

#### Scenario: DraftInput に禁止情報が含まれる
- **WHEN** `DraftInput` の生成時に内部 IP アドレスや API key が含まれる
- **THEN** 入力バリデーションがこれを検出し、provider 呼び出し前にエラーを返すこと

#### Scenario: DraftInput の許可リスト情報のみで生成する
- **WHEN** 公開 CVE 情報と文体指示のみを DraftInput に含めて provider を呼び出す
- **THEN** provider が DraftOutput を返し、audit log に `generation_input_hash` が記録されること

### Requirement: prompt / output 保存方針
システムは prompt および output の保存について以下の方針に従わなければならない（SHALL）。

保存するもの:
- `prompt_version`（バージョン識別子）
- `generation_input_hash`（入力の SHA-256 ハッシュ、原文は保存しない）  
  定義: `SHA-256(canonical_json(DraftInput の以下フィールド: advisory, references, target_audience, target_language, urgency, template_id, prompt_version))` — canonical_json はキーのアルファベット順ソート・空白なしシリアライズ
- `generated_at`（生成タイムスタンプ、ISO 8601）
- `provider_name` / `provider_type` / `model`
- validation 結果（`DraftPost.validation_warnings`）
- token / cost メタデータ（取得可能な場合）

保存してはならないもの（LLM audit log に限定）:
- prompt の原文（LLM に送った実際のテキスト）
- API key / token / Secret

補足（アプリ DB との区別）:
- DraftPost のコンテンツ（draft 本文）はアプリケーション DB に通常保存される（レビュー・承認フロー用）。これは LLM audit log の制限とは別のものである。
- LLM audit log は prompt 原文を含まず、`generation_input_hash` と validation 結果のみを記録する。

#### Scenario: LLM 生成完了後に audit log を記録する
- **WHEN** LLM provider が DraftOutput を返す
- **THEN** `generation_input_hash` / `provider_type` / `prompt_version` / `generated_at` が audit log に記録されること

#### Scenario: prompt 原文が保存されない
- **WHEN** provider が DraftOutput を返す
- **THEN** LLM に送った prompt テキストそのものがデータベースまたはログに保存されないこと

### Requirement: provider 切替方針
システムは provider の切替を設定変更のみで実現できなければならない（SHALL）。

1. `config.yml`（または環境変数）の `llm.provider` を変更することで provider を切り替えできる
2. provider の切替には実装変更（コード修正）を必要としない
3. 切替はプロセス再起動後に有効になる（live reload は不要）。切替前に実行中のリクエストは旧 provider で完了させる
4. 切替時に既存の DraftPost の `provider_type` フィールドは変更されない（immutable）
5. provider の切替は audit log に記録する

#### Scenario: provider を test_mock から production_api に切り替える
- **WHEN** `llm.provider` を `test_mock` から `production_api` に変更して再起動する
- **THEN** 以降の生成リクエストが production_api provider に送られ、切替が audit log に記録されること

#### Scenario: 未知の provider_type が設定される
- **WHEN** 設定に存在しない `provider_type` 値が指定される
- **THEN** システムは起動時バリデーションでエラーを返し、生成処理を開始してはならない

### Requirement: production_api provider の監査項目
`production_api` provider（Azure OpenAI / Foundry 等）を使用する場合、以下の監査項目をすべて記録しなければならない（SHALL）。

必須記録項目:
- `provider_name`（例: `azure-openai`）
- `provider_type`（`production_api`）
- `model`（deployment name 含む）
- `prompt_version`
- `generation_input_hash`（SHA-256）
- `generated_at`（ISO 8601 タイムスタンプ）
- `token_usage`（prompt_tokens / completion_tokens / total_tokens）
- `cost_estimate`（取得可能な場合）
- `validation_result`（output validation 結果サマリ）

禁止記録項目:
- API key / token / authorization header
- provider secret / connection string

#### Scenario: production_api で生成した場合に監査項目が完全に記録される
- **WHEN** production_api provider が正常に DraftOutput を返す
- **THEN** 上記必須記録項目がすべて audit log エントリに含まれること

#### Scenario: production_api の監査ログに Secret が混入しない
- **WHEN** production_api の audit log エントリを確認する
- **THEN** API key・authorization header・connection string が記録されていないこと

### Requirement: generic_api provider の監査項目
`generic_api` provider（OpenAI API / Anthropic API 等）を使用する場合、以下の監査項目をすべて記録しなければならない（SHALL）。

必須記録項目:
- `provider_name`（例: `openai-api`, `anthropic-api`）
- `provider_type`（`generic_api`）
- `model`（モデル ID）
- `prompt_version`
- `generation_input_hash`（SHA-256）
- `generated_at`
- `token_usage`
- `cost_estimate`（取得可能な場合）
- `validation_result`

#### Scenario: generic_api で生成した場合に監査項目が記録される
- **WHEN** generic_api provider が正常に DraftOutput を返す
- **THEN** 上記必須記録項目がすべて audit log エントリに含まれること

### Requirement: test_mock provider の監査項目
`test_mock` provider を使用する場合、以下の監査項目を記録しなければならない（SHALL）。

必須記録項目:
- `provider_name`（`test-mock`）
- `provider_type`（`test_mock`）
- `prompt_version`
- `generation_input_hash`
- `generated_at`

省略可能項目:
- `token_usage`（mock のため記録不要）
- `cost_estimate`（mock のため記録不要）

#### Scenario: test_mock で生成した場合に基本監査項目が記録される
- **WHEN** test_mock provider が DraftOutput を返す
- **THEN** `provider_type = "test_mock"` / `prompt_version` / `generation_input_hash` が audit log に記録されること

### Requirement: test_manual provider の監査項目
担当者が `test_manual` フロー（ChatGPT / Claude 手動生成）を実施した場合、以下の監査項目を手動で記録しなければならない（SHALL）。

必須記録項目:
- `provider_name`（例: `chatgpt-subscription`, `claude-subscription`）
- `provider_type`（`test_manual`）
- `prompt_version`（使用したプロンプトのバージョン識別子。手動入力時も記録する）
- `generation_input_hash`（手動入力内容の SHA-256 ハッシュ）
- `generated_at`（手動入力日時）
- `manual_review_required: true`（常に）

#### Scenario: test_manual の手動取込時に監査項目が設定される
- **WHEN** 担当者が test_manual フローで DraftPost を手動入力する
- **THEN** `provider_type = "test_manual"` と `manual_review_required = true` が設定されること

#### Scenario: test_manual の DraftPost でレビュー必須フラグが確認される
- **WHEN** 承認フローが test_manual の DraftPost を処理する
- **THEN** `manual_review_required = true` が設定されていることを確認してから次フェーズに進むこと

### Requirement: 実稼働 provider とテスト provider の明確分離
実稼働環境では production provider のみを使用しなければならない（SHALL）。

環境定義（`$APP_ENV` 環境変数で制御）:
- 有効値: `production` / `staging` / `development` / `test`
- `$APP_ENV` が未設定の場合は起動時エラーとする（未設定 = 環境不明であり、production と同等の制約を暗黙適用することは誤りの元になる）

環境 / provider_type 組み合わせルール:
- `production` 環境: `production_api` / `production_flow` / `generic_api` のみ許可。`test_mock` / `test_manual` は禁止
- `staging` 環境: `production_api` / `production_flow` / `generic_api` / `test_mock` を許可。`test_manual` は禁止
- `development` / `test` 環境: すべての provider_type を許可

provider_type と実行環境の組み合わせを起動時設定バリデーションで検証する。

#### Scenario: 本番環境で test_mock provider を設定した場合
- **WHEN** `APP_ENV=production` かつ `llm.provider = test_mock` で起動する
- **THEN** システムは設定バリデーションエラーを返し、起動を拒否しなければならない

#### Scenario: テスト環境で任意の provider を使用する
- **WHEN** `APP_ENV=test` かつ `llm.provider = test_mock` で起動する
- **THEN** システムが正常に起動し、mock provider が生成リクエストを処理すること

#### Scenario: APP_ENV 未設定時の動作
- **WHEN** `$APP_ENV` 環境変数が設定されていない状態で起動する
- **THEN** システムは起動時設定バリデーションでエラーを返し、起動を拒否しなければならない

### Requirement: build_llm_provider が generic_api provider を構築する

`build_llm_provider` 関数は `config.provider` が `"generic_api"` の場合に `GenericApiLLMProvider` を返さなければならない（SHALL）。

`"test_mock"` の挙動は変更されない。

#### Scenario: generic_api が選択されたとき GenericApiLLMProvider が返される

- **WHEN** `build_llm_provider(LLMConfig(provider="generic_api", endpoint_url=..., model=..., auth_env_var=...))` を呼ぶ
- **THEN** `GenericApiLLMProvider` のインスタンスが返される

#### Scenario: test_mock は従来どおり MockLLMProvider を返す

- **WHEN** `build_llm_provider(LLMConfig(provider="test_mock", prompt_version="v1"))` を呼ぶ
- **THEN** `MockLLMProvider` のインスタンスが返される

