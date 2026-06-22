# Azure Hosted Core

## Status

Accepted

## Context

SPAutoPost の主要ユースケースは、定期的に脆弱性情報を収集し、社内 SharePoint Site Page / News 向けの記事を作成し、管理者が確認・修正・確定した後に投稿する運用です。

この運用では、定期収集、記事生成、投稿待ち管理、投稿処理を人間ユーザーの端末に依存させるべきではありません。

## Decision

SPAutoPost の運用コアは、Azure 上の container runtime に置きます。

主候補は次の構成です。

- Azure Container Apps: Admin API / backend / lightweight management service
- Azure Container Apps Jobs: scheduled collection, draft generation, publish-approved jobs
- Azure managed storage: 将来の本番永続化候補
- Microsoft Graph: SharePoint Site Page / News 投稿
- LLM providers: provider interface 経由

CLI / Batch は、ローカル開発、dry-run、手動再実行、Container Apps Jobs の command entrypoint として残します。

## Rationale

- 定期収集や投稿処理をユーザー端末に依存させない。
- Azure 上で Secret、監査ログ、ジョブ実行履歴、ネットワーク境界を管理しやすい。
- Container Apps と Jobs を使うことで、常時稼働 API と定期実行 job を同一環境で扱いやすい。
- 早期の管理画面化に移行しやすい。
- 将来 external collector を分離しても、Azure 上の import / review / publish 基盤として残せる。

## Consequences

- MVP の CLI 実装は Azure Jobs から実行できる command 設計にする。
- ストレージは SQLite から始める場合でも、Azure hosted runtime での永続化・同時実行・バックアップを再検討する。
- 管理者レビュー UI/API は後続で早期追加する。
- GitHub Issue では、M1 に Azure Container Apps 用の deployment skeleton を追加する。
- 本番公開前に managed identity、Graph permission、Log Analytics、Secret 管理を確定する。

## Non-Goals

- MVP 初期で本格的な多人数管理画面を完成させること
- MVP 初期で複雑なジョブオーケストレーションを実装すること
- MVP 初期で本番 DB を完全確定すること

## Related

- Spec: docs/specs/architecture.md
- Spec: docs/specs/configuration.md
- Spec: docs/specs/security-baseline.md
- Spec: docs/specs/audit-log.md
- Issue: #21
- Issue: #23
