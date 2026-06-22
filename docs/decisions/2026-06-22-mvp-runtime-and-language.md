# MVP Runtime and Language

## Status

Accepted

## Context

SPAutoPost の MVP では、まず手動入力またはサンプル脆弱性情報から、正規化、AI 原稿生成、人間レビュー、SharePoint 下書きまたはテスト投稿、監査ログ記録までの縦串を通す必要があります。

この段階では、Web UI や常駐サービスよりも、実装速度、検証容易性、dry-run、監査可能性を優先します。

## Decision

MVP の実装言語は Python とします。

MVP の実行形態は CLI / Batch application とします。

画面が必要になった段階で、TypeScript / Node.js による frontend または API layer を検討します。

## Rationale

- Python は、脆弱性情報の収集、正規化、YAML/JSON、SQLite、HTTP client、LLM API 連携と相性がよい。
- CLI / Batch は MVP の縦串検証に向いている。
- Web UI、API server、常駐 worker を MVP に含めると、投稿基盤としての本質的な検証より実装面が重くなる。
- 将来、画面が必要になった場合でも、Python core を維持しつつ TypeScript / Node.js を追加できる。

## Consequences

- M0 / M1 の実装 Issue は Python CLI / Batch 前提で進める。
- `docs/specs/architecture.md` を MVP アーキテクチャの正本として扱う。
- Web UI / API server / scheduler は MVP 対象外とする。
- TypeScript / Node.js は将来の UI または API layer 候補として残す。

## Related

- Spec: docs/specs/architecture.md
- Issue: #4
- Issue: #6
- Issue: #7
- Issue: #9
- Issue: #10
