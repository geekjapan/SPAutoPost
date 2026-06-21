# SPAutoPost

SPAutoPost は GitHub 駆動で管理するプロジェクトです。

このリポジトリでは、GitHub に記載された Spec / Milestone / Issue をプロジェクトの正本として扱います。Claude Code / Codex などの実装エージェントは、Milestone に沿って Issue を OpenSpec change に落とし込み、実装・検証・Pull Request 作成を行います。

## 運用原則

1. GitHub repo に記載された内容を正本とします。
2. チャット上の議論、AI の提案、ローカル生成物は、GitHub に反映されるまでは補助情報として扱います。
3. Milestone はリリースまたは作業フェーズの単位です。
4. Issue は OpenSpec change および実装作業の単位です。
5. 実装エージェントは Issue の範囲を超えた仕様変更を行いません。
6. 仕様が不足している場合、実装エージェントは推測で進めず、Issue または Spec の更新を要求します。

## 主要ドキュメント

- [AGENTS.md](./AGENTS.md): Claude Code / Codex など実装エージェント向けの作業ルール
- [docs/project-rules.md](./docs/project-rules.md): プロジェクト全体の運用ルール
- [docs/openspec-workflow.md](./docs/openspec-workflow.md): Issue から OpenSpec change へ落とし込む手順
- [docs/specs/README.md](./docs/specs/README.md): Spec の管理方針
- [docs/decisions/README.md](./docs/decisions/README.md): 設計判断記録の管理方針

## 権威順位

仕様や判断が競合した場合の優先順位は次のとおりです。

1. ユーザーが GitHub に記載した Spec / Milestone / Issue
2. このリポジトリ内のプロジェクトルール文書
3. OpenSpec change
4. 実装コード、テスト、コメント
5. チャット上の議論や AI の提案

## 現在の状態

初期セットアップ段階です。最初の Spec / Milestone / Issue を作成した後、それに基づいて OpenSpec change と実装作業を開始します。
