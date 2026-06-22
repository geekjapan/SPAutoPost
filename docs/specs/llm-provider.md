# LLM Provider Specification

## Status

Proposed

## Purpose

この Spec は、SPAutoPost が掲示板原稿生成に利用する生成 AI provider の分類、責務、入力制限、監査項目、実稼働/テスト分離方針を定義します。

## Provider Categories

### production_api

実稼働で利用する API provider です。

候補:

- Microsoft Foundry / Azure OpenAI
- その他の業務利用可能な LLM API

要件:

- API 利用が契約・規約上許可されている
- 認証方式が明確
- 監査ログを取得または補完できる
- 業務データ投入可否が確認済み
- rate limit と error handling を実装できる

### production_flow

Copilot Studio など、workflow / agent / flow として利用する provider です。

要件:

- 入出力 schema が定義できる
- 実行履歴または監査情報を追跡できる
- SharePoint 投稿前の原稿生成用途に限定できる
- 失敗時に再試行または手動介入できる

### generic_api

OpenAI-compatible API または vendor 固有 API を抽象化して扱う provider です。

要件:

- endpoint / model / auth / request / response mapping を設定または adapter で分離する
- 非公式 API や UI scraping を使わない
- provider ごとの規約確認を前提にする

### test_mock

単体テスト、snapshot test、CI 用の deterministic provider です。

要件:

- 外部通信しない
- fixture から固定応答を返す
- prompt version や input hash の検証に使える

### test_manual

ChatGPT subscription / Claude subscription など、人間操作を前提にした検証用 provider です。

方針:

- 実稼働 provider として扱わない
- UI 自動操作、scraping、非公式自動化を前提にしない
- 業務データや社内限定情報を投入しない
- テスト用サンプル、公開情報、匿名化済み情報に限定する
- 生成結果を手動で SPAutoPost に取り込む場合は、provider_type を test_manual として記録する

## Provider Interface

推奨 interface:

```text
Provider.validateConfig(config) -> ProviderStatus
Provider.generateDraft(input: DraftInput) -> DraftOutput
Provider.getProviderMetadata() -> ProviderMetadata
Provider.estimateCost(input: DraftInput) -> CostEstimate optional
```

## DraftInput

必須項目:

- advisory: Advisory または Advisory[]
- target_audience: general_users | administrators | mixed
- target_language: ja-JP
- urgency: emergency | high | normal | low
- template_id: string
- prompt_version: string
- references: Reference[]

禁止項目:

- Secret
- token
- cookie
- authorization header
- 個人情報
- 社内限定の詳細構成情報。ただし明示的に許可された範囲を除く

## DraftOutput

必須項目:

- title
- summary_for_users
- impact
- required_actions
- references
- warnings optional

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

検査結果は DraftPost.validation_warnings に保存します。

## Audit Requirements

記録する項目:

- provider_name
- provider_type
- model or deployment name
- prompt_version
- generation_input_hash
- generated_at
- token / cost metadata if available
- validation result

記録しない項目:

- API key
- token
- provider secret
- authorization header

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

## Related Issues

- #6 Implement LLM provider interface with mock provider
- #15 Define LLM provider strategy and production/test separation
- #16 Implement Microsoft Foundry / Azure OpenAI provider adapter
- #17 Implement generic LLM API provider adapter
- #18 Add AI output validation and source-grounding checks
