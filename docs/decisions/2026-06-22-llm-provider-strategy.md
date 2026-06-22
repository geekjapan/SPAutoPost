# LLM Provider Strategy

## Status

Proposed

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

- Provider interface を先に実装する。
- mock provider を MVP に含める。
- production provider の実装は、利用条件と入力データ制限を確認してから行う。
- test_manual provider の結果は、手動投入または fixture として扱う。

## Related

- Issue: #6
- Issue: #15
- Issue: #16
- Issue: #17
- Issue: #18
- Spec: docs/specs/llm-provider.md
