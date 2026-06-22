# M1 Implementation Order

## Status

Accepted

## Context

M1 では、最低限の自動収集、記事生成、管理者確認、確定、専用 SharePoint Site Page / News 投稿までの縦串を通します。

複数の機能を同時に作るため、実装順序を固定しないと手戻りが大きくなります。

## Decision

M1 は次の順序で実装します。

1. PostgreSQL schema / migration baseline
2. Python core source and draft pipeline
3. TypeScript / Node.js Admin UI/API
4. Graph / SharePoint posting PoC
5. Azure Container Apps / Jobs deployment skeleton

Optional spike は本線を止めない範囲で並行実施します。

- Firecrawl source adapter spike
- optional LLM draft provider evaluation
- Foundry / Azure OpenAI provider spike
- generic LLM API provider spike

## Rationale

- PostgreSQL schema が先にないと、Python core と Admin UI/API の state 共有が不安定になる。
- Python core pipeline がないと、Admin UI/API で確認する DraftPost が存在しない。
- Admin UI/API がないと、管理者確認・修正・確定の運用が検証できない。
- 投稿 PoC は、承認済み DraftPost ができてから接続する方が自然である。
- Azure deployment skeleton は、ローカルと hosted runtime の差分を最後にまとめて確認しやすい。

## Related

- Spec: docs/specs/m1-mvp-scope.md
- Issue: #25
- Issue: #26
- Issue: #28
- Issue: #31
- Issue: #32
- Issue: #33
- Issue: #36
