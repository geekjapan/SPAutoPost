# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SPAutoPost** — SharePoint への自動投稿を行うツール。設計仕様（`docs/specs/`・`docs/decisions/`）は整備済みで、アプリケーションコードはこれから着手する段階。

## 正本と作業フロー

このプロジェクトは GitHub 駆動方式。正本は GitHub Issue / Milestone と、リポジトリ内の `AGENTS.md`・`docs/project-rules.md`・`docs/specs/`・`docs/decisions/`。Issue を OpenSpec change に落としてから実装する。詳細フローと権威順位は `AGENTS.md` を参照（ここでは重複させない）。

## マルチエージェント運用（adapter）

詳細は `AGENTS.md`「自律マルチエージェント運用」節と `docs/runbooks/multi-agent-orchestration.md` を正とする。ここでは Claude Code 固有の補足のみ:

- このセッションは Orca worktree 内で動作しうる（`ORCA_*` 環境変数）。1 Issue = 1 worktree = 1 OpenSpec change。
- OpenSpec-first: Issue 正本確認後、実装・レビュー・PR 作成より先に `opsx:propose` / `opsx:ff` で change を作成・更新する。既存 change がある場合も、作業前に Issue / Spec と矛盾しないことを再確認し、必要なら先に change を更新する。
- 仕様駆動スパイン: `opsx:propose` / `opsx:ff` → `openspec validate <change-id> --strict` → `self-grill-across-multi-propose`（事前ゲート）→ `opsx:apply`（TDD 手順で実装）→ `ecc:code-review` / `ecc:security-review` → PR → `opsx:archive`。
- `ecc:plan` / `ecc:feature-dev` / `ecc:code-review` などの ECC 手順は OpenSpec change の後段として使う。Issue に対応する OpenSpec change が未作成・未検証のまま実装へ進まない。
- Orca から起動された Claude worker は `--dangerously-skip-permissions` 前提でも、OpenSpec-first と carve-out（仕様不足 / 認証・認可・Secret・投稿 / Spec 差分 / セキュリティ判断）を優先する。
- OpenSpec change が Issue / Spec と矛盾する、または必要情報が欠ける場合は実装へ進まず、`decision_gate` / `escalation` で coordinator に戻す。
- 規約・チェックリストは `.claude/rules/ecc/`（common+python+typescript+web、`paths:` で自動適用）。
- agmsg: team=`spautopost`、monitor モードで受信。共有ファイル変更・依存・Spec 差分は他エージェントへ通知。
- 自律度=高（merge まで自動）。ただし仕様不足 / 認証・認可・Secret・投稿(publish) / Spec 差分 / CI 未整備 は人間ゲート（`AGENTS.md` の carve-out を参照）。

## Repository State

`src/` / `tests/` / ビルド設定はまだ無い。実装を開始する際は以下の規約に従う。

## Directory Layout (planned)

```
src/        # アプリケーションコード
tests/      # テスト（src/ と同構造でマッピング）
docs/       # 設計ノート・運用ドキュメント
assets/     # 静的ファイル（必要な場合のみ）
```

1ファイルで収まる実装から始め、複雑になったときだけ分割する。

## Commands

ランタイムは Python 3.12+。パッケージ/ツール設定は `pyproject.toml`（`[project]` / `[tool.*]`）。

```sh
# セットアップ（dev ツール込み）
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"            # または: uv pip install -e ".[dev]"

# lint / format / type / test
ruff check . && ruff format --check src tests
mypy src
pytest --cov=spautopost --cov-report=term-missing   # カバレッジ 80% 以上

# アプリ（CLI / batch entrypoint）
spautopost --env development validate-config         # python -m spautopost ... も可
spautopost show-config                               # Secret は *** で秘匿表示

# OpenSpec
openspec validate <change-id> --strict

# Git
git status --short --branch
git log --oneline -n 8
git diff
```

## Key Constraints

- SharePoint 認証情報・トークン・クレデンシャルはコードに含めない。環境変数または secrets manager を使用する。
- 生成キャッシュ・マシン固有設定もコミット対象外。
- ファイル命名: ディレクトリは小文字（`src/`, `tests/`）、ファイルは振る舞いを示す名前（例: `post_scheduler.py`, `sharepointClient.ts`）。

## Commit Style

まだ慣行が確立していない。`feat: add post scheduler` のような Conventional Commits 形式を推奨。

## Modular Rules (ECC)

詳細なコーディング規約・テスト・セキュリティ基準は `.claude/rules/ecc/` に配置（ECC 由来、チーム共有）。`common/` は言語非依存、言語別ディレクトリが `../common/` を拡張する。

| ディレクトリ | 適用範囲 |
|--------------|----------|
| `.claude/rules/ecc/common/` | 全ファイル共通（不変性・TDD80%・セキュリティ・git/PR・性能） |
| `.claude/rules/ecc/python/` | `**/*.py`（fastapi 含む） |
| `.claude/rules/ecc/typescript/` | `**/*.ts` / `**/*.tsx` |
| `.claude/rules/ecc/web/` | フロントエンド/Web 共通 |

ランタイム確定後、不要言語の削除や追加言語の導入は `~/.claude/plugins/marketplaces/ecc/rules/` からコピーする（ディレクトリ単位でコピーし、`../common/` 参照を壊さないこと）。

## Agent skills

### Issue tracker

Issues live in GitHub Issues (`geekjapan/SPAutoPost`). See `docs/agents/issue-tracker.md`.

### Specs & decisions

仕様は `docs/specs/`、設計判断（ADR 相当）は `docs/decisions/`。プロジェクト規約は `docs/project-rules.md`。
