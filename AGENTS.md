# AGENTS.md

このファイルは Claude Code / Codex など、リポジトリ上で作業する実装エージェント向けの必読ルールです。

## 最重要ルール

このプロジェクトは GitHub 駆動方式で進めます。

実装エージェントは、ユーザーが GitHub repo に記載した Spec / Milestone / Issue を正本として参照してください。チャット上の会話、AI の推測、ローカル生成物は、GitHub に反映されるまでは正本ではありません。

## 権威順位

仕様、判断、優先度が競合した場合は、次の順で判断してください。

1. GitHub の Spec / Milestone / Issue
2. `README.md`、`docs/project-rules.md`、この `AGENTS.md`
3. OpenSpec change
4. 実装コード、テスト、コメント
5. AI の提案、チャットログ、ローカルメモ

## 作業フロー

1. 対象 Milestone を確認する。
2. 対象 Issue を確認する。
3. Issue の目的、完了条件、非対象範囲、関連 Spec を確認する。
4. Issue 単位で OpenSpec change を作成または更新する。
5. OpenSpec change の内容が Issue と矛盾しないことを確認する。
6. 実装する。
7. テスト、lint、型検査、セキュリティ上の基本確認を実施する。
8. Pull Request で Issue / Milestone / OpenSpec change / 検証結果を明記する。

## Issue と OpenSpec change の対応

原則として、1 つの Issue は 1 つの OpenSpec change に対応させます。

複数 Issue を 1 つの change にまとめる場合、または 1 Issue を複数 change に分割する場合は、Issue 側に理由を明記してください。

推奨する change ID は次の形式です。

```text
issue-<issue-number>-<short-kebab-title>
```

例:

```text
issue-12-add-post-scheduler
```

## ブランチ命名

推奨形式は次のとおりです。

```text
change/<issue-number>-<short-kebab-title>
fix/<issue-number>-<short-kebab-title>
docs/<issue-number>-<short-kebab-title>
```

## 実装エージェントがしてよいこと

- Issue に明記された範囲の実装
- Issue に対応する OpenSpec change の作成・更新
- 必要なテスト、lint、型検査、ドキュメント更新
- 明らかな誤字、リンク切れ、軽微な整合性修正

## 実装エージェントがしてはいけないこと

- Issue にない仕様を独自に追加すること
- Milestone の目的を変更すること
- ユーザーが記載した Spec と矛盾する実装を行うこと
- 秘密情報、API キー、トークン、Cookie、個人情報をコミットすること
- 自動投稿、外部 API 呼び出し、アカウント操作において、権限・利用規約・レート制限を無視した実装を行うこと
- 仕様不足を推測だけで埋めて実装を進めること

## 仕様不足時の扱い

次に該当する場合は、実装を止めて Issue または Spec の更新を要求してください。

- 認証方式が未定義
- 投稿先、投稿権限、投稿対象アカウントが未定義
- 外部 API の利用条件、レート制限、失敗時動作が未定義
- 保存するデータ、保持期間、秘密情報の扱いが未定義
- 成功条件、エラー条件、ロールバック条件が未定義
- セキュリティまたは法務上の判断が必要

## セキュリティ・安全性の基本方針

SPAutoPost は、自動投稿や外部サービス連携を含む可能性があります。実装時は次を守ってください。

- 明示的に許可されたアカウント、API、投稿先だけを扱う。
- spam、なりすまし、規約回避、レート制限回避に転用される実装を避ける。
- 秘密情報は環境変数または Secret 管理に寄せ、リポジトリに保存しない。
- ログにはトークン、Cookie、認証ヘッダ、個人情報を出力しない。
- 失敗時に重複投稿しないよう、冪等性を考慮する。
- 監査可能性のため、投稿要求・結果・失敗理由は必要最小限の形で記録する。

## Pull Request の完了条件

PR には最低限、次を含めてください。

- 対応 Issue
- 対応 Milestone
- 対応 OpenSpec change
- 実装概要
- 検証結果
- 仕様差分の有無
- セキュリティ上の注意点

## 自律マルチエージェント運用（Orca + ECC + OpenSpec + agmsg）

このリポジトリは Orca（`stablyai/orca`）をマルチエージェントオーケストレータとして運用する。詳細手順は `docs/runbooks/multi-agent-orchestration.md` を正とし、ここでは要点のみ示す。

### 実行モデル

- **1 Issue = 1 Orca worktree = 1 OpenSpec change** を基本単位とする。worktree ごとに Claude Code / Codex（必要に応じ OpenCode / Pi）を起動する。
- Orca 利用時は **Orca Orchestrator を coordinator** とし、Issue 選定、worktree 作成、task dispatch、`worker_done`（作業完了通知）/ `escalation`（人間または coordinator 介入要求）/ `decision_gate`（判断待ち）、PR review 対応、merge gate、archive、次 Issue 選定を Dynamic Workflow として扱う。
- エージェントは Codex 固定ではなく、Claude Code Bypass/Yolo と Codex yolo を含む multi-runtime worker pool として使う。Orca 内で起動する実装 worker は原則 yolo/bypass 前提で、承認待ちで停止しない設計にする。
- worktree 起動時のスクリプトは `orca.yaml`（`scripts.setup` / `issueCommand` / `archive`）で共有する。
- 独立 Issue は複数 worktree で並行消化する。設計難度やリスクが高い、または方式が割れる場合は、同一 Issue を複数エージェント（Codex / Claude Code など）に並列で当て、diff を比較して優位案をマージする（採否理由を PR/Issue に残す）。
- PR review 対応、CI 失敗修正、最終 diff review は、原則として既存 Issue worktree に fresh worker terminal を追加して処理する。実装 worker とは別 runtime にレビューさせることを推奨する。

### agmsg 協調

- チームは `spautopost`。各 worktree のエージェントは固有名で参加する。
- 共有ファイル（この `AGENTS.md` / `docs/specs/` / data-model 等）へ影響する変更の着手前、依存・ブロック発生時、Spec 差分発生時は agmsg で他エージェントへ通知する。
- 合意・決定はチャットに留めず、Issue / Spec / `docs/decisions/` に反映する（チャットは正本ではない）。

### スキル起動（ハーネス別）

- Claude Code: 計画 `ecc:plan`、仕様化 `opsx:propose`/`opsx:ff`、事前ゲート `self-grill-across-multi-propose`、適用/実装 `opsx:apply`（TDD 手順）、レビュー `ecc:code-review`、セキュリティ `ecc:security-review`、同期/完了 `opsx:sync`/`opsx:archive`。規約は `.claude/rules/ecc/`。
- Codex: `AGENTS.md` をネイティブに読む。OpenSpec は `.codex/skills`、agmsg 受信は `.codex/hooks.json`（Stop フック）。事前ゲート・レビュー・セキュリティは本ファイルと runbook のチェックリストに準拠する。
- Orca 上の Claude Code 実装 worker も OpenSpec-first とする。Issue 正本確認後、`opsx:propose` / `opsx:ff` で change を作成・更新し、`openspec validate <change-id> --strict`、事前ゲートを経て、`opsx:apply` の中で TDD 手順により実装する。

### 自律度と人間ゲート

既定の自律度は **高（merge まで自動）**。CI がグリーンで、かつ次の carve-out に該当しない change は PR から merge まで自動で進めてよい。**投稿（publish）は常に人間承認**。

auto-merge せず必ず人間にエスカレーションする条件:

- 「仕様不足時の扱い」に該当する仕様不足。
- 認証 / 認可 / Secret / 投稿（publish）に触れる変更。
- 権威順位の競合、または Spec 差分を伴う変更。
- セキュリティ・法務判断が必要なもの。
- **auto-merge の実効化には branch protection で必須ステータスチェック（CI）を設定する**。CI ワークフロー（`.github/workflows/ci.yml`）は整備済みだが、必須チェック未設定の間は PR 作成 → 人間 merge にフォールバックする。

## エージェント設定ファイルの扱い

- このファイル（`AGENTS.md`）が repo workflow の単一正本。`CLAUDE.md` は Claude Code 用の薄い adapter として追従させる。workflow / 権威順位 / Issue・OpenSpec 方針を変える場合は、まず `AGENTS.md` を更新し、`CLAUDE.md` には差分要約または参照だけを置く。
- `.agents/skills` は共有/互換用の追加 skill 面であり、各 runtime 固有の `.claude/skills`・`.codex/skills`・`.opencode/skills`・`.pi/skills` と完全一致させる必要はない。

Issue の完了条件を満たしていない PR は、完了扱いにしません。
