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
       └─ Orca Orchestrator task DAG
            └─ Orca worktree       ← Issue から worktree 作成（orca.yaml issueCommand 起動）
                 └─ worker pool (Claude Code Bypass/Yolo / Codex yolo / 必要に応じ OpenCode / Pi)
                 └─ OpenSpec change        ← opsx:propose（change ID = issue-<n>-<kebab>）
                      └─ 事前ゲート          ← self-grill-across-multi-propose
                           └─ 実装 + 検証     ← tdd / code-review / security-review
                                └─ PR
                                     └─ auto-merge ゲート（carve-out 該当時は人間）
```

Orca 起動後は、Issue queue を順次消化する常駐コックピットとして運用する。人間が都度 Issue を選ぶのではなく、Orchestrator が Issue の分類、worktree wave、worker dispatch、PR review 対応、merge gate、archive、次 Issue 選定までを回す。

### Dynamic Workflow

Orchestrator の task DAG は次を標準形とする。

```text
parent: issue-<n> lifecycle
  -> classify / source-of-truth check
  -> OpenSpec change
  -> implementation
  -> verification
  -> diff review
  -> commit / PR create
  -> PR review fix
  -> CI / review recheck
  -> merge gate
  -> archive worktree
  -> next issue selection
```

- 各 worker は dispatch ごとに `worker_done` を 1 回だけ返す。`worker_done` は coordinator への完了通知、`decision_gate` は続行判断待ち、`escalation` は人間または coordinator 介入要求を表す。
- ブロック時は `decision_gate` / `escalation` を使い、ローカル TUI の質問で停止しない。
- 長時間 task は heartbeat を返す。coordinator は timeout を失敗扱いせず、terminal activity / task state / inbox を確認して継続判断する。
- PR review fix、CI failure fix、security review は同じ Issue lifecycle の子 task として扱い、完了後に merge gate へ戻す。
- workflow の正本は GitHub Issue / Milestone / Spec であり、Orchestrator task や worker prompt は実行管理メモにすぎない。

## 1. Orca worktree 運用

- **1 Issue = 1 worktree = 1 OpenSpec change** を基本単位とする。
- worktree 作成時に `orca.yaml` の `setup` が走り、`git fetch`・openspec 確認・agmsg 案内を行う。
- Issue 紐付き起動では `issueCommand` が仕様駆動ループの開始手順を提示する。
- **parallel Issue wave**: 依存関係がない Issue は複数 worktree で同時に進めてよい。
- **fan-out / merge-winner**: 設計難度が高い、または方式が割れる change では、同一 Issue を複数エージェント（例: Claude Code Bypass/Yolo と Codex yolo）に並列で当て、diff を比較して優位案をマージする。採否理由は PR または Issue に残す。
- **review-fix worker**: PR review 対応や CI 失敗修正は、原則として既存 Issue worktree に fresh terminal を追加して行う。実装 worker と別 runtime にレビューさせるときは、編集範囲を明示する。
- **shared-file serialization**: `AGENTS.md`、`docs/specs/`、data model、config、migration など共有ファイルに触る task は agmsg / Orchestrator で衝突予告し、必要なら順序化する。
- ブランチ命名は `AGENTS.md` に従う: `change|fix|docs/<issue-number>-<short-kebab-title>`。
- worktree 撤去時は `archive` が未マージ change / PR / agmsg 未読の確認を促す。

## 2. Worker pool / runtime 運用

Codex に固定せず、Orca 上の multi-runtime worker pool として扱う。

| Runtime | 主な用途 | 起動前提 |
|---------|----------|----------|
| Codex | 実装、テスト、OpenSpec、CI / review fix | yolo |
| Claude Code | 設計レビュー、実装代替案、diff review、複雑 Issue の fan-out | Bypass/Yolo |
| OpenCode / Pi | 必要時の補助 worker | `AGENTS.md` 継承 |

- Orchestrator が coordinator であり、worker runtime は実行手段にすぎない。
- Orca 内で起動する実装 worker は、承認待ちで停止しない yolo/bypass 前提で起動する。
- Orchestrator は Secret、認証情報、実 publish、外部アカウント操作を必要とする task を yolo/bypass worker に直接 dispatch しない。必要な場合は人間 gate 付き task として分離し、worker には最小権限の環境変数・設定だけを渡す。
- hooks は事前確認済みのものだけを承認済みとして扱う。Secret や外部 publish につながる hook / tool は carve-out として人間 gate に回す。
- 同一 Issue の fan-out では、各 candidate worktree の採否理由、落とした案、採用差分を PR または Issue に残す。
- PR 前 review は、実装 worker とは別 runtime に投げることを推奨する。狭い修正なら同じ runtime の fresh terminal でもよい。
- Claude Code 実装 worker も OpenSpec-first で起動する。Issue 正本確認後に `opsx:propose` / `opsx:ff` で change を作成・更新し、`openspec validate <change-id> --strict`、事前ゲートを経て、`opsx:apply` の中で TDD 手順により実装する。`ecc:*` はこの後段の計画・レビュー・修正用に限定し、OpenSpec change 未作成・未検証のまま実装しない。

### Worker 起動の安定パターン

長文の task preamble を `orca orchestration dispatch --inject` で Codex / Claude Code TUI へ直接流すと、runtime や TUI 状態によっては入力欄に残り、送信確定されないことがある。Orca 上で実装 worker を確実に自律走行させる場合は、次の順を既定とする。

1. Issue worktree を作成する。
2. その worktree に fresh shell terminal を作成する。
3. `orca orchestration dispatch --task ... --to <terminal> --from <coordinator>` で lifecycle tracking だけを作る（`--inject` は使わない）。
4. 返却された `taskId` / `dispatchId` / coordinator handle を埋め込んだ prompt file を `/tmp` に作る。
5. shell terminal へ `codex --dangerously-bypass-approvals-and-sandbox --dangerously-bypass-hook-trust "$(cat <prompt-file>)"` または `claude --dangerously-skip-permissions "$(cat <prompt-file>)"` を送る。
6. worker は prompt file 内の `worker_done` / `decision_gate` / `escalation` コマンドだけで coordinator と通信する。

`--inject` は短い手動 review prompt など、送信状態を terminal read で確認できる場合に限って使う。

Claude worker の prompt file には次の順序を明記する:

1. GitHub Issue / Milestone / 関連 Spec を正本として確認する。
2. 対応 OpenSpec change を `opsx:propose` / `opsx:ff` で作成または更新する。
3. `openspec validate <change-id> --strict` を通す。
4. `self-grill-across-multi-propose` で依存・競合・carve-out を確認する。
5. `opsx:apply` の中で TDD 実装し、必要に応じて `ecc:*` 手順（計画・レビュー等）を使う。
6. PR には Issue / Milestone / OpenSpec change / 検証結果 / 仕様差分 / セキュリティ注意点を記録する。

## 3. agmsg 協調プレイブック

- チームは `spautopost`。各 worktree のエージェントは固有名で参加する（例: `claude-m1-scheduler`, `codex-m1-connector`）。
- **メッセージを送る場面**:
  - 共有ファイル（`AGENTS.md` / specs / data-model）に影響する変更を始める前（衝突予告）。
  - 別 Issue/change の成果物に依存する、またはブロックされたとき。
  - Spec 差分や設計判断（ADR 相当）が発生し、他 change に波及するとき。
- **受信**: Claude Code は monitor モード（リアルタイム）、Codex は Stop フック（`.codex/hooks.json`）で受信する。
- 重要な合意・決定はチャットに留めず、Issue / Spec / `docs/decisions/` に反映する（チャットは正本ではない）。

## 4. ECC スキル / エージェント起動マップ

| フェーズ | Claude Code | Codex |
|----------|-------------|-------|
| 計画 | `ecc:plan` / `ecc:planner` agent | AGENTS.md + 手動計画 |
| 仕様化 | `opsx:propose` / `opsx:ff`（実装前に必須） | `openspec-propose`（`.codex/skills`） |
| 事前ゲート | `self-grill-across-multi-propose` | 同等の自己レビュー（チェックリスト） |
| 実装 | `opsx:apply`（TDD 手順） / `ecc:feature-dev` | TDD 手順を AGENTS.md 準拠で実施 |
| レビュー | `ecc:code-review` / `code-reviewer` agent | `code-review`（差分レビュー） |
| セキュリティ | `ecc:security-review` / `security-reviewer` agent | security-review runbook 準拠 |
| デバッグ | `diagnosing-bugs` | 同等の調査ループ |
| 同期/完了 | `opsx:sync` / `opsx:archive` | `openspec-apply-change` 他 |

- ルール（規約・チェックリスト）は `.claude/rules/ecc/`（common + python + typescript + web）。
- `paths:` グロブにより、`**/*.py` 等の実コードに自動適用される。

## 5. 自律度と人間ゲート

既定の自律度は **高（merge まで自動）**: CI がグリーンで、かつ下記 carve-out に該当しない change は PR 作成から merge まで自動で進めてよい。投稿（publish）は常に人間承認（`docs/runbooks/operation.md`）。

### auto-merge せず必ず人間にエスカレーションする条件（carve-out）

- 仕様不足（`AGENTS.md`「仕様不足時の扱い」該当）。
- 認証 / 認可 / Secret / 投稿（publish）に触れる変更。
- 権威順位の競合（GitHub 正本と change/実装が矛盾）。
- Spec 差分を伴う変更（先に Spec / Issue / OpenSpec を更新）。
- セキュリティ / 法務上の判断が必要。
- **必須チェック未設定の間**: CI ワークフロー（`.github/workflows/ci.yml`: ruff / mypy / pytest+coverage / gitleaks）は整備済み。auto-merge を実効化するには branch protection で必須ステータスチェックを設定する。それまでは「PR 作成 → 人間 merge」にフォールバックする。

## 6. 失敗対応

- **エージェント停止 / 競合**: Orca で該当 worktree を確認し、`git status` と OpenSpec change の整合を確認。復旧不能なら worktree を破棄し Issue から再作成。
- **並列マージ衝突**: 共有ファイルは agmsg で予告 → 順序化。衝突発生時は最新 main に rebase し、change の整合を再確認。
- **CI 失敗**: `ecc:build-fix` / 各言語 build-resolver で最小修正。原因が仕様起因なら carve-out としてエスカレーション。
- **誤投稿**: `docs/runbooks/incident-response.md` と `operation.md`「Correction Procedure」に従う。

## 7. 停止手順

- 全エージェント停止が必要な場合: Orca で全 worktree のエージェントを停止し、未マージ PR を確認。
- 投稿系の緊急停止は `operation.md`「Stop Procedure」に従う（scheduler 停止・publish 無効化）。

## 8. 関連ドキュメント

- `AGENTS.md`（実装エージェント向け単一正本）
- `docs/openspec-workflow.md`（Issue → OpenSpec change 手順）
- `docs/project-rules.md`（プロジェクト全体ルール）
- `docs/runbooks/operation.md`（運用・投稿・停止）
- `docs/runbooks/security-review.md`（セキュリティレビュー）
- `docs/runbooks/incident-response.md`（インシデント対応）
- `orca.yaml`（Orca worktree スクリプト設定）
