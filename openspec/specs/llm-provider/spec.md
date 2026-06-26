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

- 採用する vendor（OpenAI API / Anthropic API / 他）が決定されている
- 当該 vendor の利用条件・データ保持方針が業務利用上問題ないと確認されている
- OpenAI-compatible endpoint の adapter 設計が完了している
- 認証方式が確定している
- rate limit・失敗時動作・SLA が確認されている
- 監査ログ取得方法が確定している

#### Scenario: M3 着手前に generic API 前提条件を確認する
- **WHEN** Issue #17 (generic API provider) の実装を開始する
- **THEN** 上記 6 点の前提条件が Issue #17 に記録・承認されていること
