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

### 手動 advisory 入力

YAML / JSON の手動入力を検証し、既存の Advisory model へ正規化した preview を確認できます。
このコマンドは外部 API 呼び出し、SharePoint 投稿、永続化を行いません。

```sh
spautopost --dry-run import-advisory samples/advisories/manual-cve.yaml
spautopost --dry-run import-advisory samples/advisories/manual-advisory.json
```

### dry-run preview と監査ログ

手動 advisory から原稿を生成し、SharePoint へ送る予定の payload（Site Page 必須セクション）と
最小監査イベントを実投稿せずに確認できます。`test_mock` provider で生成し、外部 API 呼び出し、
SharePoint 投稿、Secret 解決、永続化は行いません。投稿先識別子（`env:` 参照）と Secret は
`***` に秘匿します。

```sh
spautopost preview-draft samples/advisories/manual-cve.yaml
```

出力には投稿予定 payload と、provider 名 / provider type / prompt version /
generation_input_hash / operation / result を含む監査イベント（`publish_dry_run`）が含まれます。
生成が失敗した場合は error_code / error_message を持つ `error` イベントを表示します。

### Admin API skeleton（TypeScript / Node.js）

M1 の Admin API skeleton は `admin-api/` にあります。DraftPost の read は PostgreSQL を直読みし、
edit / approve / reject / request regeneration / publish request は `AdminCommand` を enqueue します。
実 SharePoint 投稿、Microsoft Graph 呼び出し、本番 Entra ID/OIDC はこの skeleton では実行しません。

```sh
npm ci
npm run admin-api:check

export SPAUTOPOST_DATABASE_URL='<postgresql-database-url>'
PORT=3000 node admin-api/dist/src/main.js
```

state-changing request には client 供給の `Idempotency-Key` と、開発用 principal header が必要です。
本番の Entra ID login / role mapping は #29 の対象です。

```sh
curl -X POST http://127.0.0.1:3000/api/drafts/draft-1/approve \
  -H 'content-type: application/json' \
  -H 'x-spautopost-user: local-reviewer' \
  -H 'x-spautopost-roles: approver' \
  -H 'Idempotency-Key: local-retry-key-1' \
  -d '{"comment":"reviewed"}'
```

## ストレージとマイグレーション

ストレージは ORM 非依存の repository ポート（`StoragePort`）越しに使用します。
backend は `storage.provider` で選択し、`config` の必須フィールドを factory が検証します。

- `provider: sqlite` … ローカル/テスト用（stdlib `sqlite3`、追加依存なし）。`storage.sqlite_path` 必須。
- `provider: postgresql` … 本番想定。`storage.database_url` 必須。psycopg は postgres 分岐でのみ
  遅延 import されるため、optional extra のインストールが必要です。

```sh
# PostgreSQL backend を使う場合は postgres extra を追加インストールする
pip install -e ".[dev,postgres]"
```

スキーマの正本は方言別の SQL migration ファイル（`db/migrations/{postgres,sqlite}/NNNN_*.sql`）です。
ORM 自動生成には依存しません。両方言は同一テーブル/制約集合を持ち、テストの
schema-equivalence で同期を検証します（`audit_events.event_type` の列挙は `docs/specs/audit-log.md`
の 15 値が正本）。

migration ランナーは `schema_migrations(version, checksum, applied_at)` を冪等にブートストラップし、
version 昇順に 1 ファイル 1 トランザクションで適用します。適用済みファイルの SHA-256 ドリフトを
検知すると停止します（`MigrationDriftError`）。

```sh
# 未適用 migration の一覧のみ表示（DDL は適用しない）
spautopost --dry-run migrate

# アクティブ provider に baseline migration を適用（再実行は no-op）
spautopost --no-dry-run migrate
```

> PostgreSQL backend の contract suite はローカルでは skip し、CI（Postgres service +
> `SPAUTOPOST_TEST_DATABASE_URL`）で sqlite と postgres の両方を実 DB で検証します。
> ローカルで postgres backend まで含めたフルカバレッジを取りたい場合は、以下で
> PostgreSQL を起動してから `SPAUTOPOST_TEST_DATABASE_URL` を設定して pytest を実行します。
>
> ```sh
> docker run --rm -e POSTGRES_PASSWORD=spautopost -e POSTGRES_DB=spautopost \
>   -p 5432:5432 postgres:16
> export SPAUTOPOST_TEST_DATABASE_URL=postgresql://postgres:spautopost@localhost:5432/spautopost
> pytest -q --cov=spautopost --cov-report=term-missing
> ```
>
> postgres backend を skip したローカル実行でも全体 80% ゲートは満たしますが、
> `src/spautopost/storage/postgres_backend.py` のカバレッジは PG service が有る CI で
> 担保されます（CI ゲートが正本）。

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
