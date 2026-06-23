# SPAutoPost

SPAutoPost は、社内 SharePoint サイトのお知らせ掲示板に、セキュリティ対策情報、脆弱性情報、その対応方法を掲載するための自動化プログラムです。

当面は、脆弱性情報の収集、対策方針の整理、掲示板向け文章の生成、SharePoint への下書きまたは投稿までをこのプログラム内に実装します。将来的には、クローラーや情報整理を別プログラムへ分離し、SPAutoPost は正規化済み情報を安全に SharePoint へ掲載する投稿基盤に責務を絞ることを想定します。

このリポジトリは GitHub 駆動で管理します。

このリポジトリでは、GitHub に記載された Spec / Milestone / Issue をプロジェクトの正本として扱います。Claude Code / Codex などの実装エージェントは、Milestone に沿って Issue を OpenSpec change に落とし込み、実装・検証・Pull Request 作成を行います。

## MVP アーキテクチャ方針

MVP の core language は Python とし、最小実装単位は CLI / Batch command とします。

ただし、定期的な情報収集、記事生成、投稿待ち管理、投稿処理は人間ユーザーの端末に依存させず、Azure Container Apps / Azure Container Apps Jobs を主候補とする Azure hosted runtime に寄せます。

SharePoint への掲載方式は、SharePoint Site Page / News article 形式を採用します。

## 運用原則

1. GitHub repo に記載された内容を正本とします。
2. チャット上の議論、AI の提案、ローカル生成物は、GitHub に反映されるまでは補助情報として扱います。
3. Milestone はリリースまたは作業フェーズの単位です。
4. Issue は OpenSpec change および実装作業の単位です。
5. 実装エージェントは Issue の範囲を超えた仕様変更を行いません。
6. 仕様が不足している場合、実装エージェントは推測で進めず、Issue または Spec の更新を要求します。

## 主要ドキュメント

- [AGENTS.md](./AGENTS.md): Claude Code / Codex など実装エージェント向けの作業ルール
- [docs/design-documents.md](./docs/design-documents.md): 設計書面の一覧、状態、関連 Issue
- [docs/product-brief.md](./docs/product-brief.md): プロダクトの目的、対象、成功条件
- [docs/roadmap.md](./docs/roadmap.md): 推奨 Milestone と段階的ロードマップ
- [docs/features.md](./docs/features.md): 機能分解
- [docs/project-rules.md](./docs/project-rules.md): プロジェクト全体の運用ルール
- [docs/openspec-workflow.md](./docs/openspec-workflow.md): Issue から OpenSpec change へ落とし込む手順
- [docs/specs/README.md](./docs/specs/README.md): Spec 一覧と管理方針
- [docs/specs/initial-system.md](./docs/specs/initial-system.md): 初期システム仕様
- [docs/specs/architecture.md](./docs/specs/architecture.md): Azure hosted core / MVP アーキテクチャ仕様
- [docs/specs/sharepoint-publishing.md](./docs/specs/sharepoint-publishing.md): SharePoint Site Page / News 投稿仕様
- [docs/specs/data-model.md](./docs/specs/data-model.md): 正規化データモデル仕様
- [docs/specs/llm-provider.md](./docs/specs/llm-provider.md): LLM provider 仕様
- [docs/specs/draft-composition.md](./docs/specs/draft-composition.md): 掲示板原稿仕様
- [docs/specs/security-baseline.md](./docs/specs/security-baseline.md): セキュリティ baseline
- [docs/specs/audit-log.md](./docs/specs/audit-log.md): 監査ログ仕様
- [docs/decisions/README.md](./docs/decisions/README.md): 設計判断記録の管理方針
- [docs/runbooks/operation.md](./docs/runbooks/operation.md): 運用 runbook
- [docs/runbooks/security-review.md](./docs/runbooks/security-review.md): セキュリティレビュー runbook
- [docs/runbooks/incident-response.md](./docs/runbooks/incident-response.md): インシデント対応 runbook
- [docs/runbooks/multi-agent-orchestration.md](./docs/runbooks/multi-agent-orchestration.md): Orca + ECC + OpenSpec + agmsg による自律マルチエージェント運用 runbook
- [orca.yaml](./orca.yaml): Orca worktree スクリプト設定（setup / issueCommand / archive）

## 起動方法（開発）

Python 3.12 以上を使用します。Secret はコードに含めず、`config/*.yml`（gitignore 対象）と環境変数で管理します。

```sh
# 1. 仮想環境と依存（dev ツール込み）を用意する
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

# 2. 設定サンプルをコピーして編集する（実 config は gitignore される）
cp config.example.yml config/default.yml

# 3. Secret は環境変数で渡す（config には env:NAME 参照のみ）
export SPAUTOPOST_TENANT_ID=...
export SPAUTOPOST_SHAREPOINT_SITE_ID=...
export SPAUTOPOST_SHAREPOINT_PAGE_LIBRARY_ID=...

# 4. 設定を検証する（CLI / batch entrypoint。将来は Azure Container Apps Jobs の command）
spautopost --env development validate-config
# または: python -m spautopost --env development validate-config

# 設定内容を Secret 秘匿付きで確認する
spautopost show-config

# dry-run は既定で有効（true の間は SharePoint へ投稿しない）。明示切替も可能:
spautopost --dry-run validate-config
spautopost --no-dry-run validate-config   # publish は人間ゲート対象
```

検証コマンド（lint / type / test）:

```sh
ruff check . && ruff format --check src tests
mypy src
pytest --cov=spautopost --cov-report=term-missing   # カバレッジ 80% 以上を要求
```

## 権威順位

仕様や判断が競合した場合の優先順位は次のとおりです。

1. ユーザーが GitHub に記載した Spec / Milestone / Issue
2. このリポジトリ内のプロジェクトルール文書
3. OpenSpec change
4. 実装コード、テスト、コメント
5. チャット上の議論や AI の提案

## 現在の状態

初期設計セットアップ段階です。M0 では Azure hosted core、SharePoint Site Page / News 投稿方式、データモデル、セキュリティ baseline、監査ログ、設定方針を確定し、その後 M1 の MVP 実装へ進みます。
