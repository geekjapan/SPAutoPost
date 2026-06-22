# MVP Runtime and Language

## Status

Accepted

## Context

SPAutoPost の MVP では、定期的に脆弱性情報を収集し、記事を作成し、管理者が確認・修正・確定した後、SharePoint Site Page / News として投稿する運用を目指します。

この運用では、定期収集や投稿処理を人間ユーザーの端末に依存させるべきではありません。常時起動または定期起動できる Azure 上の container runtime を運用コアに据える必要があります。

一方で、初期実装と検証では CLI / Batch command が有効です。CLI は開発、dry-run、手動再実行、障害時の補助操作、Container Apps Jobs の command entrypoint として残します。

## Decision

MVP の core language は Python とします。

MVP の最小実装単位は Python CLI / Batch command とします。

ただし、運用コアはユーザー端末ではなく Azure Container Apps / Azure Container Apps Jobs を主候補とします。

管理者が記事を確認・修正・確定する UI/API は早期に追加する方針とします。管理画面が必要になった段階で TypeScript / Node.js を採用します。

## Rationale

- Python は、脆弱性情報の収集、正規化、YAML/JSON、HTTP client、LLM API 連携と相性がよい。
- CLI / Batch は MVP の縦串検証に向いている。
- 定期収集や投稿処理をユーザー端末に依存させると、可用性、監査性、認証情報管理、再現性の面で弱い。
- Azure Container Apps / Jobs を使うと、常時稼働 API と定期 job を同一 Azure 環境上で扱いやすい。
- 将来、管理画面が必要になった場合でも、Python core を維持しつつ TypeScript / Node.js の UI/API layer を追加できる。

## Consequences

- M0 / M1 の実装 Issue は Python core + CLI command 前提で進める。
- ただし、CLI は最終運用形ではなく Azure Jobs の entrypoint として設計する。
- 定期収集、記事生成、投稿待ち管理は Azure hosted runtime へ寄せる。
- Web UI / API server は MVP 初期の必須ではないが、早期追加対象とする。
- `docs/specs/architecture.md` を MVP アーキテクチャの正本として扱う。
- TypeScript / Node.js は将来の Admin UI / API layer 候補として残す。

## Related

- Spec: docs/specs/architecture.md
- Issue: #4
- Issue: #6
- Issue: #7
- Issue: #9
- Issue: #10
- Issue: #21
- Issue: #23
