# LLM Provider Specification

## Status

Accepted (Issue #15 — 2026-06-26 確定)

## M1 Scope Decision

Issue #35 Spike 評価の結果、以下のスコープを確定する。

| provider_type | M1 扱い | 備考 |
|---|---|---|
| `test_mock` | **必須** | Issue #6 で実装、CI/テスト基盤 |
| `test_manual` | optional（手動取込のみ） | UI 自動化・非公式 API 利用禁止 |
| `production_api` (Azure OpenAI / Foundry) | **M3 以降** | Issue #16、M3 前提条件を先に満たすこと |
| `generic_api` (OpenAI-compatible) | **M3 以降** | Issue #17、provider ごとに利用条件確認が必要 |
| `production_flow` (Copilot Studio) | **M3 以降** | 別途検討 |

**根拠:**
- M1 の完了条件は mock/template による DraftPost 生成であり、LLM API は必須でない
- Azure OpenAI / Foundry の利用条件・入力データ許容範囲・Entra ID 認証の確認は M1 期間内に保証できない
- generic API は provider ごとに利用条件が異なり、adapter 設計には interface 確定が先行必要
- Spike 期間中に API 接続テストを実施しない（本番データ不使用、環境未整備）

## Purpose

この Spec は、SPAutoPost が掲示板原稿生成に利用する生成 AI provider の分類、責務、入力制限、監査項目、実稼働/テスト分離方針を定義します。本 Spec は Issue #16（Azure OpenAI provider）・#17（generic API provider）・#18（AI output validation）の実装契約です。

## 用語定義

provider_type の分類で混同しやすい用語を明確にします。

| 用語 | 意味 | 分類 |
|---|---|---|
| **ChatGPT subscription** | chat.openai.com の Web UI を人間が手動操作するサービス | `test_manual` |
| **OpenAI API** | api.openai.com の公式 REST API（プログラム呼び出し） | `generic_api`（利用条件確認必要） |
| **Claude subscription** | claude.ai の Web UI を人間が手動操作するサービス | `test_manual` |
| **Anthropic API** | api.anthropic.com の公式 REST API（プログラム呼び出し） | `generic_api`（利用条件確認必要） |
| **Azure OpenAI / Foundry** | Microsoft が提供する enterprise 向け LLM API | `production_api` |
| **Copilot Studio** | Microsoft の workflow / flow ベースの AI agent | `production_flow` |

## Provider Categories

### production_api

実稼働で利用する API provider です（Microsoft Foundry / Azure OpenAI 等）。

**SHALL 要件:**

1. API 利用が社内情報セキュリティ部門によって承認されている
2. 利用する API の規約上、業務データの投入が許可されている
3. Entra ID managed identity または組織が管理する API key で認証している（コードへの直書き禁止）
4. rate limit・タイムアウト・エラーハンドリングを実装している
5. 監査ログを取得または補完できる手段が確保されている

承認状態は設定ファイルのフラグで表現します。共通フラグは `llm.production_approved: true` であり、このフラグが `true` でない場合、起動時設定バリデーションが `production_api` / `production_flow` / `generic_api` の使用をブロックします。

`production_api`（Azure OpenAI / Foundry）は Azure 固有設定として `llm.azure.production_approved: true` も承認源として受け入れます。ただし、これは情報セキュリティ部門の承認取得を代替するものではなく、取得済み承認を設定で表現するためのフラグです。フラグの設定は情報セキュリティ部門の承認取得後に担当者が行い、その事実を Issue / ADR に記録します。

### production_flow

Copilot Studio など、workflow / agent / flow として利用する provider です。

**SHALL 要件:**

1. 入出力 schema が定義できる
2. 実行履歴または監査情報を追跡できる
3. SharePoint 投稿前の原稿生成用途に限定される
4. 失敗時に自動リトライまたは担当者へのアラートを発する（サイレント無視禁止）

### generic_api

OpenAI-compatible API または vendor 固有 API を抽象化して扱う provider です（OpenAI API / Anthropic API 等）。

**SHALL 要件:**

1. endpoint / model / auth / request / response mapping を設定または adapter で分離している
2. 公式 API のみを使用する。非公式 API や UI scraping は禁止
3. 採用 vendor の利用規約・データ保持方針が業務利用上問題ないと情報セキュリティ部門が確認している
4. 認証情報は環境変数または Secret store 経由でのみ参照する

### test_mock

単体テスト、snapshot test、CI 用の deterministic provider です。

**SHALL 要件:**

1. 外部ネットワーク通信を行わない
2. fixture から固定応答を返し、出力が決定的（deterministic）である
3. prompt version および input hash の検証に使用できる
4. CI 環境で Secret なしで動作する

### test_manual

ChatGPT subscription / Claude subscription など、人間操作を前提にした検証用 provider です。

**方針:**

- 実稼働 provider として扱わない
- UI 自動操作、scraping、非公式自動化を前提にしない
- 業務データや社内限定情報を投入しない
- テスト用サンプル、公開情報、匿名化済み情報に限定する
- 生成結果を手動で SPAutoPost に取り込む場合は、`provider_type` を `test_manual` として記録する

**MUST NOT（絶対禁止）:**

1. ブラウザ自動操作、Selenium、Playwright 等による UI 自動化
2. 非公式 API、reverse-engineered endpoint の利用
3. 業務データ（実 CVE 詳細、社内ネットワーク構成、未公開インシデント情報等）の LLM への投入
4. レビュー・承認フローを経ずに生成結果を SharePoint へ直接公開
5. `provider_type` を記録せずに DraftPost を生成すること

#### M1 手動取込フロー

1. 担当者が ChatGPT / Claude subscription でサンプルデータ（公開情報・匿名化済み情報）を使い手動生成する
2. 生成結果を DraftPost として SPAutoPost に手動入力する
3. DraftPost の `provider_type` を `test_manual` に設定し audit log に記録する
4. レビュー・承認フローを経て SharePoint に投稿する（自動公開禁止）

## ChatGPT / Claude Subscription の非自動化方針

ChatGPT / Claude subscription（Web UI）は実稼働自動化 provider として扱ってはならない（**MUST NOT**）。

- 本 provider の利用は `test_manual` 分類に限定する
- 自動化・スケジュール実行・batch 処理の用途に使用しない
- 本 provider で生成した結果を経由して別の自動化フローをトリガーしない
- 設定ファイルで `llm.provider = "production_api"` として登録しようとした場合、起動時バリデーションでブロックする

## Provider Interface

確定 interface（M1 で固定、mock provider #6 の実装基準）:

```text
Provider.validate_config() -> ProviderStatus
Provider.generate_draft(input: DraftInput) -> DraftOutput
Provider.get_provider_metadata() -> ProviderMetadata
Provider.estimate_cost(input: DraftInput) -> CostEstimate | None  # optional
```

### ProviderMetadata

```text
{
  provider_name: str,
  provider_type: "production_api" | "production_flow" | "generic_api" | "test_mock" | "test_manual",
  model: str | None,
  prompt_version: str | None
}
```

### ProviderStatus

```text
{
  valid: bool,
  issues: list[str],
  metadata: ProviderMetadata
}
```

## DraftInput

必須項目:

- advisory: Advisory または Advisory[]（参照: `docs/specs/data-model.md`）
- target_audience: general_users | administrators | mixed
- target_language: ja-JP
- urgency: emergency | high | normal | low
- template_id: string
- prompt_version: string
- references: Reference[]（参照: `docs/specs/data-model.md`）

## LLM 入力制限（許可リスト / 禁止リスト）

LLM provider（production_api / generic_api / test_manual すべてに適用）に渡す入力は最小化しなければならない（**SHALL**）。

`DraftInput` に含めてよい情報（許可リスト）:

- 公開された脆弱性情報（CVE / JVN / vendor advisory の要約）
- 一般公開されている参考 URL
- 一般化された社内向け文体指示・フォーマット指定
- 明示的に情報セキュリティ部門が許可した製品名またはカテゴリ
- urgency / target_audience / target_language 等のメタデータ
- prompt_version / template_id 等の制御パラメータ

`DraftInput` に含めてはならない情報（禁止リスト）:

- API key / access token / client secret / authorization header / cookie（認証情報全般）
- 個人識別情報（PII: 氏名・メールアドレス・社員番号等）
- 社内ネットワーク構成（内部 IP / hostname / VLAN / サブネット等）
- 認証方式の詳細（LDAP 構成、AD OU 構造、MFA 設定等）
- 未公開インシデント情報（報告前の社内セキュリティ障害等）
- 攻撃者に有益な内部防御状況（EDR 製品名・設定・検知ルール詳細等）
- 社内限定の詳細構成情報（例: 非公開 GitHub リポジトリ URL、内部 wiki hostname、未承認製品名等）
- 攻撃手順・PoC 詳細・脆弱性の悪用手法（生成抑制のためプロンプトに含めない）

`Advisory` / `Reference` 型が含めてよい情報の範囲は `docs/specs/data-model.md` を参照すること。

## DraftOutput

必須項目:

- title
- summary_for_users
- impact
- required_actions
- references
- warnings (optional)

推奨項目:

- admin_actions
- deadline
- uncertainty_notes
- source_mapping
- validation_hints

## Prompt Requirements

prompt は version 管理します。

必須要件:

- 出典にない事実を断定しない
- 攻撃手順、PoC、悪用詳細を生成しない
- 一般利用者向け対応と管理者向け対応を分ける
- パッチ適用、回避策、確認方法は出典に基づく
- 不確実な点は不確実と表現する
- 緊急度表現は入力された urgency に従う

## Output Validation

LLM 出力は、そのまま公開しません。

検査項目:

- required sections
- reference presence
- unsupported claims
- dangerous detail
- overstatement
- missing mitigation
- missing affected product
- hallucinated URL

検査結果は `DraftPost.validation_warnings` に保存します。検査の深刻度は以下のとおりです:

- **BLOCK**: `dangerous_detail`・`hallucinated_url` が検出された場合、DraftPost のステータスを `blocked` にし、レビュー担当者による手動確認が完了するまで承認フローを進めない
- **WARN**: それ以外の検査項目は警告として記録するが、承認フローをブロックしない（担当者がレビュー時に参照する）

`Failure Handling` の `provider_output_validation_failed` エラーは BLOCK 判定時に発生します。

## Prompt / Output 保存方針

システムは prompt および output の保存について以下の方針に従わなければならない（**SHALL**）。

**LLM audit log に記録するもの:**

- `prompt_version`（バージョン識別子）
- `generation_input_hash`（入力の SHA-256 ハッシュ、原文は保存しない）  
  定義: `SHA-256(canonical_json(DraftInput の advisory, references, target_audience, target_language, urgency, template_id, prompt_version フィールド))` — canonical_json はキーのアルファベット順ソート・空白なしシリアライズ
- `generated_at`（ISO 8601 タイムスタンプ）
- `provider_name` / `provider_type` / `model`
- `validation_result`（output validation 結果サマリ）
- `token_usage`（取得可能な場合）
- `cost_estimate`（取得可能な場合）

**LLM audit log に保存してはならないもの:**

- prompt の原文（LLM に送った実際のテキスト）
- API key / token / Secret

**補足（アプリ DB との区別）:**

DraftPost のコンテンツ（draft 本文）はアプリケーション DB に通常保存される（レビュー・承認フロー用）。これは LLM audit log の制限とは別のものです。LLM audit log は prompt 原文を保存しませんが、上記の必須記録項目（`prompt_version`・`generation_input_hash`・`generated_at`・`provider_name` / `provider_type` / `model`・`validation_result`）はすべて記録します。

## Provider 切替方針

システムは provider の切替を設定変更のみで実現できなければならない（**SHALL**）。

1. `config.yml`（または環境変数）の `llm.provider` を変更することで provider を切り替えできる
2. provider の切替には実装変更（コード修正）を必要としない
3. 切替はプロセス再起動後に有効になる（live reload は不要）。切替前に実行中のリクエストは旧 provider で完了させる
4. 切替時に既存の DraftPost の `provider_type` フィールドは変更されない（immutable）
5. provider の切替は audit log に記録する
6. 存在しない `provider_type` 値が設定された場合、起動時バリデーションでエラーを返す

## Audit Requirements

provider_type ごとの監査項目を以下に定義します。

### production_api の監査項目

**必須記録項目:**

- `provider_name`（例: `azure-openai`）
- `provider_type`（`production_api`）
- `model`（deployment name 含む）
- `prompt_version`
- `generation_input_hash`（SHA-256）
- `generated_at`（ISO 8601）
- `token_usage`（prompt_tokens / completion_tokens / total_tokens）
- `cost_estimate`（取得可能な場合）
- `validation_result`（output validation 結果サマリ）

**禁止記録項目:**

- API key / token / authorization header
- provider secret / connection string

### generic_api の監査項目

**必須記録項目:**

- `provider_name`（例: `openai-api`, `anthropic-api`）
- `provider_type`（`generic_api`）
- `model`（モデル ID）
- `prompt_version`
- `generation_input_hash`（SHA-256）
- `generated_at`
- `token_usage`
- `cost_estimate`（取得可能な場合）
- `validation_result`

**禁止記録項目:**

- API key / token / authorization header
- provider secret / connection string

### test_mock の監査項目

**必須記録項目:**

- `provider_name`（`test-mock`）
- `provider_type`（`test_mock`）
- `prompt_version`
- `generation_input_hash`
- `generated_at`

**省略可能項目:**

- `token_usage`（mock のため記録不要）
- `cost_estimate`（mock のため記録不要）

### test_manual の監査項目

担当者が手動取込する際、以下の監査項目を必ず記録しなければならない（**SHALL**）。

**必須記録項目:**

- `provider_name`（例: `chatgpt-subscription`, `claude-subscription`）
- `provider_type`（`test_manual`）
- `prompt_version`（使用したプロンプトのバージョン識別子。手動取込時も記録する）
- `generation_input_hash`（手動取込時も DraftInput に基づいて記録する）
- `generated_at`（手動入力日時）
- `manual_review_required: true`（常に）

## 実稼働 / テスト環境分離方針

実稼働環境では production provider のみを使用しなければならない（**SHALL**）。

**環境定義（`$APP_ENV` 環境変数）:**

| `$APP_ENV` 値 | 許可される provider_type |
|---|---|
| `production` | `production_api` / `production_flow` / `generic_api` |
| `staging` | `production_api` / `production_flow` / `generic_api` / `test_mock` |
| `development` | すべて |
| `test` | すべて |

- `$APP_ENV` が未設定の場合は起動時エラーとする（未設定 = 環境不明であり、production と同等の制約を暗黙適用することは誤りの元になる）
- 有効値以外の `$APP_ENV` 値も起動時エラーとする
- 許可されない組み合わせは起動時設定バリデーションでブロックする

## Failure Handling

代表的な失敗:

- provider_config_invalid
- provider_auth_failed
- provider_rate_limited
- provider_timeout
- provider_response_invalid
- provider_policy_blocked
- provider_output_validation_failed

retryable かどうかを error に付与します。

## M3 Preconditions for Production Providers

Azure OpenAI / Foundry provider (#16) および generic API provider (#17) の実装着手前に、以下の前提条件をすべて満たし Issue に記録・承認されていること:

### Azure OpenAI / Foundry (#16)

- [ ] 社内 CVE 情報等の入力データ許容範囲（許可フィールド: CVE ID / タイトル / 要約 / CVSS スコア / ベンダーパッチ情報）を情報セキュリティ部門が承認している
- [ ] 認証方式（Entra ID managed identity または API key）が確定している
- [ ] rate limit・失敗時動作・SLA が確認されている
- [ ] 監査ログ取得方法（Azure Monitor / Log Analytics 等）が確定している
- [ ] 利用契約・データ処理契約の業務利用可否が確認されている

### generic API provider (#17)

- [ ] 社内 CVE 情報等の入力データ許容範囲（許可フィールド: CVE ID / タイトル / 要約 / CVSS スコア / ベンダーパッチ情報）を情報セキュリティ部門が承認している
- [ ] 採用する vendor（OpenAI API / Anthropic API / 他）が決定されている
- [ ] 当該 vendor の利用条件・データ保持方針が業務利用上問題ないと確認されている
- [ ] 各 vendor（OpenAI API / Anthropic API / 他）向け adapter 設計（interface 定義・error mapping・cost 推定ロジック・vendor 固有認証フロー）が完了している
- [ ] 認証方式が確定している
- [ ] rate limit・失敗時動作・SLA が確認されている
- [ ] 監査ログ取得方法が確定している

## Related Issues

- #6 Implement LLM provider interface with mock provider
- #15 Define LLM provider strategy and production/test separation
- #16 Implement Microsoft Foundry / Azure OpenAI provider adapter
- #17 Implement generic LLM API provider adapter
- #18 Add AI output validation and source-grounding checks
