# Multi-Agent Orchestration Runbook

## Status

Draft

## Purpose

この runbook は、SPAutoPost を **Orca + ECC + OpenSpec + agmsg** で、自律的・マルチエージェント・仕様駆動に運用するための標準手順を定義します。対象エージェントは Claude Code と Codex（OpenCode / Pi も `AGENTS.md` を継承）。

正本は GitHub Issue / Milestone / Spec です（`AGENTS.md` 権威順位）。本 runbook は運用層であり、正本と矛盾する場合は正本が優先します。

## 構成要素

| 要素 | 役割 | 入口 |
|------|------|------|
| Orca (`stablyai/orca`) | git worktree ごとの並列エージェント実行・比較・マージ | `orca.yaml`, Orca app |
| OpenSpec | Issue を実装可能な change に落とす仕様駆動スパイン | `opsx:*` / `openspec-*` skills |
| ECC | エージェント・スキル・ルール・レビュー資産 | plugin (`ecc:*`), `.claude/rules/ecc/` |
| agmsg | エージェント間メッセージング・協調 | `/agmsg`（team=spautopost） |

## 自律ループ

```text
GitHub Milestone
  └─ GitHub Issue                  ← 正本
       └─ Orca worktree            ← Issue から worktree 作成（orca.yaml issueCommand 起動）
            └─ agent (Claude Code / Codex)
                 └─ OpenSpec change        ← opsx:propose（change ID = issue-<n>-<kebab>）
                      └─ 事前ゲート          ← self-grill-across-multi-propose
                           └─ 実装 + 検証     ← tdd / code-review / security-review
                                └─ PR
                                     └─ auto-merge ゲート（carve-out 該当時は人間）
```

## 1. Orca worktree 運用

- **1 Issue = 1 worktree = 1 OpenSpec change** を基本単位とする。
- worktree 作成時に `orca.yaml` の `setup` が走り、`git fetch`・openspec 確認・agmsg 案内を行う。
- Issue 紐付き起動では `issueCommand` が仕様駆動ループの開始手順を提示する。
- **fan-out / merge-winner**: 設計難度が高い、または方式が割れる change では、同一 Issue を複数エージェント（例: Claude Code と Codex）に並列で当て、diff を比較して優位案をマージする。採否理由は PR または Issue に残す。
- ブランチ命名は `AGENTS.md` に従う: `change|fix|docs/<issue-number>-<short-kebab-title>`。
- worktree 撤去時は `archive` が未マージ change / PR / agmsg 未読の確認を促す。

## 2. agmsg 協調プレイブック

- チームは `spautopost`。各 worktree のエージェントは固有名で参加する（例: `claude-m1-scheduler`, `codex-m1-connector`）。
- **メッセージを送る場面**:
  - 共有ファイル（`AGENTS.md` / specs / data-model）に影響する変更を始める前（衝突予告）。
  - 別 Issue/change の成果物に依存する、またはブロックされたとき。
  - Spec 差分や設計判断（ADR 相当）が発生し、他 change に波及するとき。
- **受信**: Claude Code は monitor モード（リアルタイム）、Codex は Stop フック（`.codex/hooks.json`）で受信する。
- 重要な合意・決定はチャットに留めず、Issue / Spec / `docs/decisions/` に反映する（チャットは正本ではない）。

## 3. ECC スキル / エージェント起動マップ

| フェーズ | Claude Code | Codex |
|----------|-------------|-------|
| 計画 | `ecc:plan` / `ecc:planner` agent | AGENTS.md + 手動計画 |
| 仕様化 | `opsx:propose` / `opsx:ff` | `openspec-propose`（`.codex/skills`） |
| 事前ゲート | `self-grill-across-multi-propose` | 同等の自己レビュー（チェックリスト） |
| 実装 | `tdd` / `ecc:feature-dev` | TDD 手順を AGENTS.md 準拠で実施 |
| レビュー | `ecc:code-review` / `code-reviewer` agent | `code-review`（差分レビュー） |
| セキュリティ | `ecc:security-review` / `security-reviewer` agent | security-review runbook 準拠 |
| デバッグ | `diagnosing-bugs` | 同等の調査ループ |
| 適用/同期 | `opsx:apply` / `opsx:sync` / `opsx:archive` | `openspec-apply-change` 他 |

- ルール（規約・チェックリスト）は `.claude/rules/ecc/`（common + python + typescript + web）。
- `paths:` グロブにより、`**/*.py` 等の実コードに自動適用される。

## 4. 自律度と人間ゲート

既定の自律度は **高（merge まで自動）**: CI がグリーンで、かつ下記 carve-out に該当しない change は PR 作成から merge まで自動で進めてよい。投稿（publish）は常に人間承認（`docs/runbooks/operation.md`）。

### auto-merge せず必ず人間にエスカレーションする条件（carve-out）

- 仕様不足（`AGENTS.md`「仕様不足時の扱い」該当）。
- 認証 / 認可 / Secret / 投稿（publish）に触れる変更。
- 権威順位の競合（GitHub 正本と change/実装が矛盾）。
- Spec 差分を伴う変更（先に Spec / Issue / OpenSpec を更新）。
- セキュリティ / 法務上の判断が必要。
- **CI 未整備の間**: 現状 `src/` も CI も未作成のため、auto-merge は成立しない。CI が導入されるまでは「PR 作成 → 人間 merge」にフォールバックする。

## 5. 失敗対応

- **エージェント停止 / 競合**: Orca で該当 worktree を確認し、`git status` と OpenSpec change の整合を確認。復旧不能なら worktree を破棄し Issue から再作成。
- **並列マージ衝突**: 共有ファイルは agmsg で予告 → 順序化。衝突発生時は最新 main に rebase し、change の整合を再確認。
- **CI 失敗**: `ecc:build-fix` / 各言語 build-resolver で最小修正。原因が仕様起因なら carve-out としてエスカレーション。
- **誤投稿**: `docs/runbooks/incident-response.md` と `operation.md`「Correction Procedure」に従う。

## 6. 停止手順

- 全エージェント停止が必要な場合: Orca で全 worktree のエージェントを停止し、未マージ PR を確認。
- 投稿系の緊急停止は `operation.md`「Stop Procedure」に従う（scheduler 停止・publish 無効化）。

## 7. 関連ドキュメント

- `AGENTS.md`（実装エージェント向け単一正本）
- `docs/openspec-workflow.md`（Issue → OpenSpec change 手順）
- `docs/project-rules.md`（プロジェクト全体ルール）
- `docs/runbooks/operation.md`（運用・投稿・停止）
- `docs/runbooks/security-review.md`（セキュリティレビュー）
- `docs/runbooks/incident-response.md`（インシデント対応）
- `orca.yaml`（Orca worktree スクリプト設定）
