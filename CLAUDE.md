# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SPAutoPost** — SharePoint への自動投稿を行うツール。設計仕様（`docs/specs/`・`docs/decisions/`）は整備済みで、アプリケーションコードはこれから着手する段階。

## 正本と作業フロー

このプロジェクトは GitHub 駆動方式。正本は GitHub Issue / Milestone と、リポジトリ内の `AGENTS.md`・`docs/project-rules.md`・`docs/specs/`・`docs/decisions/`。Issue を OpenSpec change に落としてから実装する。詳細フローと権威順位は `AGENTS.md` を参照（ここでは重複させない）。

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

ビルド・テスト・リントのコマンドは、ランタイムが決まった時点でここに追記する（導入コミットと同時に記載すること）。

現時点で使用できるコマンド：

```sh
git status --short --branch   # 作業前の状態確認
git log --oneline -n 8        # 最近のコミット確認
git diff                      # 変更内容確認
```

## Key Constraints

- SharePoint 認証情報・トークン・クレデンシャルはコードに含めない。環境変数または secrets manager を使用する。
- 生成キャッシュ・マシン固有設定もコミット対象外。
- ファイル命名: ディレクトリは小文字（`src/`, `tests/`）、ファイルは振る舞いを示す名前（例: `post_scheduler.py`, `sharepointClient.ts`）。

## Commit Style

まだ慣行が確立していない。`feat: add post scheduler` のような Conventional Commits 形式を推奨。

## Agent skills

### Issue tracker

Issues live in GitHub Issues (`geekjapan/SPAutoPost`). See `docs/agents/issue-tracker.md`.

### Specs & decisions

仕様は `docs/specs/`、設計判断（ADR 相当）は `docs/decisions/`。プロジェクト規約は `docs/project-rules.md`。
