# Spec: llm-provider-evaluation

## Purpose

LLM provider の Spike 評価（Issue #35）の結果を記録し、後続 Issue (#16, #17) の実装判断根拠として参照できる状態にする。Azure OpenAI / Foundry・generic API・test_manual の M1/M3 採用可否と根拠を `docs/specs/llm-provider.md` および ADR に明文化する。

## Requirements

### Requirement: Provider evaluation result recorded in docs
Spike 評価結果（各 provider の M1/M3 判断、採用可否根拠）は `docs/specs/llm-provider.md` に追記し、後続 Issue (#16, #17) の判断根拠として参照できる状態にしなければならない（SHALL）。

#### Scenario: Azure OpenAI / Foundry の M1 見送り判断が記録される
- **WHEN** Spike 評価が完了する
- **THEN** `docs/specs/llm-provider.md` に「Azure OpenAI / Foundry は M1 に含めず M3 以降とする」旨と理由が記載されていること

#### Scenario: generic API provider の評価結果が記録される
- **WHEN** Spike 評価が完了する
- **THEN** `docs/specs/llm-provider.md` に generic API provider の M1/M3 判断と前提条件が記載されていること

#### Scenario: test_manual provider の手動取込フローが記録される
- **WHEN** Spike 評価が完了する
- **THEN** `docs/specs/llm-provider.md` に test_manual provider の M1 における手動取込フローと禁止事項が明文化されていること

### Requirement: ADR updated with M1 scope decision
`docs/decisions/2026-06-22-llm-provider-strategy.md` は Spike 評価結果に基づき M1 スコープ（mock のみ必須、LLM API は M3 以降）を明示しなければならない（SHALL）。

#### Scenario: ADR に M1 スコープが反映される
- **WHEN** Spike 評価完了後に ADR を更新する
- **THEN** ADR の Consequences セクションに「M1: mock provider のみ必須。Azure OpenAI / Foundry / generic API は M3 以降。test_manual は手動取込のみ許可」と記載されていること

### Requirement: M1/M3 decision not blocked by missing API credentials
Spike 評価は、Azure OpenAI / Foundry の API 資格情報または本番環境アクセスなしに完了できなければならない（SHALL）。評価は公開ドキュメント・利用条件・既知の認証方式情報に基づき実施する。

#### Scenario: API 資格情報なしで評価が完了する
- **WHEN** Spike 評価を実施する
- **THEN** 実際の API 呼び出しを行わず、公開情報のみで M1/M3 判断を記録できること
