## Context

Issue #6 は LLM provider の抽象化と mock provider の実装が対象であり、実 provider 接続は対象外。既存コードは stdlib dataclass / Protocol を使う方針なので、同じ形で最小実装する。

## Decisions

- `src/spautopost/llm/` に DTO、Protocol、mock provider、factory を置く。
- DTO は frozen dataclass とし、Secret・token・cookie・authorization header を保持しない前提の項目だけにする。
- `MockLLMProvider` は外部通信せず、`DraftOutput` fixture を受け取り、その値を返す。fixture 未指定時は入力から deterministic な fallback draft を組み立てる。
- config の `llm.provider` は Issue #6 の provider type 名を正とし、既存の `mock` / `azure_openai` / `generic` は引き継がない。
- factory は Issue #6 範囲の `test_mock` のみ構築し、それ以外の provider type は interface 上表現できるが未実装として validation 結果に出す。

## Risks / Trade-offs

- 実 provider 用の認証・endpoint・model 設定はまだ定義しない。Issue #16 / #17 で追加する。
- mock fallback の本文は production quality を狙わない。Issue #8 の draft composition template で本文品質を扱う。

## Verification

- config validation unit test で provider type の許容値と未知値拒否を確認する。
- LLM provider unit test で Protocol 相当の method、deterministic mock、fixture response、validation 結果、factory selection を確認する。
- `openspec validate issue-6-implement-llm-provider-interface --strict` を通す。
