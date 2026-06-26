# LLM Provider Strategy

## Status

Accepted (Issue #35 Spike 評価により M1 スコープ確定 — 2026-06-26)

## Context

SPAutoPost は、社内 SharePoint 掲示板向け原稿の作成に生成 AI を利用します。実稼働では Copilot Studio、Microsoft Foundry / Azure OpenAI、その他 LLM API を利用する可能性があります。一方、テスト用途では ChatGPT subscription や Claude subscription を使う可能性があります。

## Decision

実稼働 provider とテスト provider を分離します。

- 実稼働は production_api / production_flow / generic_api のいずれかとして扱う。
- ChatGPT / Claude subscription は test_manual として扱い、実稼働自動化 provider にしない。
- 非公式 API や UI の機械的操作を前提にした provider は実装しない。
- AI 出力は人間レビュー前提とし、自動公開しない。

## Rationale

- provider ごとに契約、利用条件、監査性、API 安定性、データ投入可否が異なる。
- チャット UI の手動利用と API provider は運用上の性質が異なる。
- 社内掲示板に掲載する情報は説明責任が必要であり、provider metadata と prompt version を追跡する必要がある。

## Consequences

- Provider interface を先に実装する（M1 で確定版を spec に反映済み）。
- **M1**: `test_mock` provider のみ必須（Issue #6）。`test_manual` は手動取込のみ optional で許可。
- **M3 以降**: `production_api`（Azure OpenAI / Foundry — Issue #16）および `generic_api`（OpenAI-compatible — Issue #17）を実装する。実装着手前に `docs/specs/llm-provider.md` の「M3 Preconditions」をすべて満たすこと。
- `production_flow`（Copilot Studio 等）は M3 以降で別途検討する。
- test_manual provider の結果は、手動投入のみで自動公開しない。業務データ・社内限定情報の LLM への投入を禁止する。
- AI 出力は人間レビュー前提とし、自動公開しない（全 milestone 共通）。

## Related

- Issue: #6
- Issue: #15
- Issue: #16
- Issue: #17
- Issue: #18
- Spec: docs/specs/llm-provider.md
