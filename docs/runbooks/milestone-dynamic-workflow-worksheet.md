# Milestone-driven Dynamic Workflow — 運用ワークシート

Orca worktree を使った Milestone 単位の並列実装ループの運用手順書 兼 周回ごとの記入シート。
設計思想は `docs/openspec-workflow.md` を、権威順位は `AGENTS.md` を正本とする。本書は「実際に回すときの手順とゲート」を定義する。

---

## 0. 用語と固定ルール（毎回変わらない前提）

| 概念 | 実体 | 補足 |
|---|---|---|
| コーディネーター | main worktree の自分（このセッション） | DAG計画・dispatch・統合・再計画を担う。`task-list --ready` を外部メモリにする |
| 実装ワーカー | **Orca worktree terminal**（`--agent` 付き） | ファイル書込を伴う実装は必ずこれ。隔離が要る |
| レビューワー | **Task `code-reviewer` subagent**（読み取りのみ） | worktree は立てない。diff を読むだけなので安く速い |
| 変更契約 | OpenSpec Change（`opsx:propose`） | 最小作業単位 |
| 状態の正本 | GitHub Milestone / Issue | 毎周ここから状態を再導出する（メモリに溜めない） |

**固定ルール（例外なし）**

1. **schema / migration を触る Change は常に直列・単一ワーカー**。並列にしない（migration 順序・同一テーブルで必ず衝突する）。
2. **実装=worktree terminal、レビュー=Task subagent**。混ぜない。
3. **ローカル green は「その変更単独で green」でしかない**。統合後に全体テストを必ず1回回す。
4. **N回差し戻しで human escalate**（§12）。Orca は1タスク3連続失敗で circuit-break するので、それ以下に上限を置く。

### 使用スキル / agent 対応表（この名前以外を使わない）

| 局面 | 正確な起動名 | 種別 |
|---|---|---|
| Milestone 理解・要件明確化・Change への分解 | `opsx:explore` | skill |
| Change proposal 作成 | `opsx:propose` | skill |
| Change 単位の事前自己検証 | `self-grill-with-docs` | skill |
| 横断の事前自己検証 / 依存DAG整合 | `self-grill-across-multi-propose` | skill（`--without-me` / `--on-unresolved=issue\|force`） |
| 人間への一括グリル（escalation） | `grill-me` | skill |
| 実装（TDD） | `tdd` | skill |
| 事後レビュー | `code-reviewer` | **agent**（`Agent(subagent_type:"code-reviewer")`） |
| バグ対応 | `diagnose` | skill |
| 完了検証 | `opsx:verify` | skill |
| アーカイブ | `opsx:archive` | skill |

`openspec:*` という名前は存在しない。必ず `opsx:*`。

---

## 1. 周回ヘッダ（記入欄）

```
Milestone        : __________________________
周回 (iteration) : #____  日付: __________
Autonomy mode    : [ ] gated   [ ] autonomous   ← §2 参照
並列上限          : ____（既定 3。レビュー処理能力で決める）
対象 Issue        : #__ #__ #__ #__ ...
状態再導出済み    : [ ] gh issue list / opsx list / git branch -a を確認した
```

---

## 2. Autonomy mode（最初に1回決める）

3 モード。**既定は adaptive**（自走しつつ、不明点が危険水準まで溜まったら一括で人間にグリルする）。

| | **gated** | **adaptive（既定・推奨）** | **autonomous** |
|---|---|---|---|
| 通常進行 | 各ゲートで人間確認 | 自走（self-grill が codebase から自己回答） | 完全自走 |
| 不明点 | 都度人間 | **unknowns ledger に溜め、閾値超で一括 `grill-me`**（§2.1） | `--without-me --on-unresolved=force` で握り潰さず issue 化 |
| 統合コンフリクト | 人間に上げる | 元 Change へ差し戻し、N回 or 高リスクで escalate | 自動差し戻し、N回で escalate |
| コーディネーター | 手動 `check --wait` | 手動 `check --wait`（escalate 時のみ人間） | `orca orchestration run --max-concurrent N` |
| 向き | 重要 Milestone / 探索的 | 大半のケース | trivial 中心 / 夜間バッチ |

### 2.1 adaptive の発火条件 — unknowns ledger

走行中に出た不明点を**1つの台帳**に溜める。各項目に blast radius を付ける。

```
# unknowns ledger（この周回）
- [ ] <unknown>           blast: low/med/high   source: explore/propose/grill/apply
- [ ] ...
```

**自走を続ける**: low/med の unknown は self-grill 系（`self-grill-with-docs` / `self-grill-across-multi-propose`）が codebase・docs から自己回答する。解けたら ledger から消す。

**人間を一括グリル（`grill-me`）する**: 次のいずれかを満たした瞬間に、**溜まった unknown をまとめて** `grill-me` に出す（都度ではなく batch）。

1. **high blast の unknown が1件でも残った** — 共有契約 / schema / security / 認証 / Milestone 到達条件に関わる
2. **未解決 unknown が閾値（既定 3 件）を超えた**
3. **手戻りリスク** — 既にマージ済みの成果を無効化しうる前提が unresolved
4. `self-grill-across-multi-propose` が `--on-unresolved` で未解決を残した

→ `grill-me` の回答を該当 Change / `CONTEXT.md` / decisions に反映 → ledger をクリアして再開。

> 狙い: 「破綻リスク・大幅手戻りリスクが上がったら人間に聞く」を、都度中断でも全自走でもなく **危険水準でのバッチ escalation** として実装する。self-grill が安く潰せるものは自走、人間にしか答えられない genuine input gap だけを一括で上げる。

---

## 3. リスク階層（Change ごとに付与）— ゲートの重さを変える

| tier | 条件 | cross-grill (§5) | 事後レビュー (§9) |
|---|---|---|---|
| **trivial** | doc / 単一ファイル / テスト追加のみ・可逆 | スキップ | 軽量（1パス） |
| **standard** | 通常の機能・複数ファイル | wave条件次第 | 通常 |
| **critical** | schema / security / 共有契約 / 認証 | 必須 | **敵対的に厚く**（独立レビューワー） |

記入:

```
Change                         | tier      | 変更ファイル集合（DAG用）
-------------------------------+-----------+----------------------------
opsx/<change-a>                | standard  | src/foo.ts, src/foo.test.ts
opsx/<change-b>                | critical  | prisma/schema.prisma  ← 直列固定
...
```

---

### 3.6 モデル割当（役割 × tier）

| 役割 | モデル / effort | 起動 |
|---|---|---|
| 最上位オーケストレータ（= main コーディネーター） | **Opus 4.8 / xHigh** | このセッション |
| 実装ワーカー: **critical** tier | **Opus 4.8 / High** | Orca `worktree create --agent claude` |
| 実装ワーカー: **standard** tier | **GPT-5.5 / High** | Orca `--agent codex` |
| 実装ワーカー: **trivial** tier | **Sonnet 4.6 / High**（任意で Medium に下げ可） | Orca `--agent claude` |
| レビュアー | **コーダーと別モデル / High**（下記 independence rule） | §9 |

**independence rule（レビュアー）**

- reviewer のモデル ≠ その Change を書いた coder のモデル。
- **critical はできれば cross-family**: coder=Opus → reviewer=GPT-5.5、coder=GPT-5.5 → reviewer=Opus。

**制約（重要・混同しない）**

- **Task subagent は Claude 系のみ**（Opus/Sonnet/Haiku/Fable）。`Agent(subagent_type:"code-reviewer", model:"sonnet")` は可、GPT 指定は不可。
- 安価な独立レビュー = coder(Opus/GPT) → **reviewer = Sonnet 4.6 の Task subagent**（worktree 不要）。
- **GPT-5.5 を reviewer にしたい場合のみ** Task ではなく **Orca codex terminal**（読み取りプロンプト、`--inject` 不要）で立てる。critical の cross-family レビューだけここに振る。
- 既定の寄せ方: **critical=Opus4.8 / standard=GPT-5.5 / trivial=Sonnet4.6**。standard は GPT-5.5 に寄せる（coder=GPT-5.5 → reviewer は Sonnet 4.6 Task subagent で自動的に別モデルになり、選択が周回ごとにブレない）。

---

### 3.5 Dynamic Workflow は誰が作るか（新規スキルを作らない）

「Dynamic Workflow を生成する専用スキル」は作らない。実体は **2 つの既存スキル出力 + コーディネーター scheduling** に分解できる。新フォーマットや永続成果物は持たない（状態は GitHub / opsx change dir / git branch から毎周再導出）。

| Dynamic Workflow の構成要素 | 担当 |
|---|---|
| Milestone 理解・Issue の目的/影響/リスク把握・Change への分解粒度決め | **`opsx:explore`**（OPSX native の探索フェーズ。要件明確化が本職。`CONTEXT.md`/decisions を更新） |
| 依存 DAG・共有契約整合・所有重複・直列/並列の妥当性 | **`self-grill-across-multi-propose`**（apply前ゲートとして既に走る。ここが DAG の権威的な検証兼抽出を兼ねる） |
| 並列度・wave の確定 | コーディネーター（§6 の 1 行ルールに上記2つの出力を食わせるだけ） |

**タイミング**: ループ step2 の「Dynamic Workflow 生成」は実は2段階。
- **早期のラフ計画**（どの Issue を今周回で扱うか・ざっくり順序）= `opsx:explore` + コーディネーター triage。軽量。
- **権威的な DAG** は propose 後に `self-grill-across-multi-propose` の出力として確定する（依存・競合はそこで初めて固まる）。§6 はこの確定 DAG を消費する。

> つまり「Dynamic Workflow を作るスキル」を探すより、`opsx:explore` で入口を、`self-grill-across-multi-propose` で DAG を出させ、scheduling は §6 のルールに任せるのが最小構成。

---

## 4. Issue → Change 分解 & propose

各 Issue を最小仕様変更単位へ分解し `opsx:propose`。AGENTS.md の作業フロー4–5に従い、Issue と矛盾しないことを確認。

- [ ] 全対象 Issue を Change 化した
- [ ] 各 Change に tier を付けた（§3）
- [ ] 各 Change の「変更ファイル集合」を見積もった（DAG の入力）

---

## 5. 事前ゲート（self-grill）

**5a. Change 単位**（全 Change）

```
self-grill-with-docs   # Issue意図/既存仕様矛盾/受け入れ条件/前提・非目標/テスト可能性/範囲過不足
```

**5b. 横断**（起動条件あり — 過剰起動しない）

> 起動するのは **同一 wave で 2 件以上 propose ∧ ドメイン領域が重なる** とき**だけ**。単独・独立 Change には不要。

```
self-grill-across-multi-propose            # gated
self-grill-across-multi-propose --without-me --on-unresolved=force   # autonomous
```

確認: 分割粒度 / 重複・矛盾 / 依存漏れ / 直列化すべきものを並列化していないか / 同一領域競合 / Milestone 到達に不足な Change。

- [ ] 5a 完了　- [ ] 5b 起動条件を判定（起動 / スキップ: ______）　- [ ] 未解決ゼロ（gated は人間確認）

---

## 6. DAG とディスパッチ集合の決定（並列度の実ルール）

形式化しない。1行ルールに畳む:

```
ready 集合 = 依存解決済み  ∧  変更ファイル集合が他の in-flight と非交差
並列度     = min(|ready|, 並列上限, レビュー処理能力)
※ schema/migration を含む Change は ready でも単独直列で流す
```

記入（この wave で流すもの）:

```
wave #__ : [ <change-a>, <change-d> ]   交差なし確認済み: [ ]
直列キュー: [ <change-b: schema> ] → [ <change-e: 同領域> ]
```

---

## 7. ワーカー起動 & dispatch（Orca）

各 ready Change につき:

```bash
orca worktree create --name <change-slug> --agent claude --json          # worktree+agent 同時
orca terminal list --worktree id:<newWorktreeId> --json                  # ハンドル取得
orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 60000 --json
orca orchestration task-create --spec "opsx:apply <change> / TDD / 所有: <領域> / schema migrate 禁止 / worker_done で報告" --json
orca orchestration dispatch --task <task_id> --to <handle> --inject --json
```

- [ ] wave の全ワーカーを起動した（並列上限まで）

---

## 8. 実装（ワーカー側 = opsx:apply + TDD）

ワーカーは preamble に従い、テスト先行 → 実装 → テスト/型/lint/関連検証 → `worker_done` を**1回だけ**送る（失敗時も送る）。

---

## 9. 完了待ち & 事後レビュー（マージ前 diff）

```bash
orca orchestration check --wait --types worker_done,escalation,decision_gate --timeout-ms 900000 --json
```

- タイムアウト / `{count:0}` は **失敗ではなくチェックポイント**。terminal が生きていれば待ち続ける。ハートビート＝生存であって完了ではない。
- `worker_done` を受けたら、その Change の **マージ前 diff** をレビュー:
  - tier=critical → 独立した `code-reviewer` Task subagent で**敵対的に**
  - それ以外 → 1パス軽量
- 確認: proposal 通り実装か / 受け入れ条件充足 / テストが仕様を検証 / 既存破壊なし / 過剰・仕様外実装なし / セキュリティ・責務分離 / 他 Change との副作用。
- NG → §12 の差し戻し。OK → §10 へ。

```
worker_done 受領: <change> | review: [ ] pass [ ] reject → 差し戻し回数 ___/N
```

---

## 10. ★統合ゲート（設計で抜けていた中核ステップ）

レビュー通過 Change を**依存順**に統合する。

```bash
# 依存の浅い順に1本ずつ
git -C <main worktree> merge --no-ff <change-branch>
# コンフリクト → そのブランチは統合せず §12 で元 Change へ差し戻し
```

統合後、**全体テストを1回**（worktree 内ローカル green は単独 green でしかない）:

```
[ ] 統合後 full test green
[ ] 統合後 型/lint green
[ ] スモーク（該当すれば）
```

- 全体テストが落ちた → 直近統合分を疑い差し戻し or 修正 Change を新規 propose。
- schema/migration Change は**必ず最初に単独統合**してから他を載せる。

---

## 11. 反映

- [ ] GitHub Issue を更新（完了条件・PR・検証結果）
- [ ] OpenSpec change を完了状態へ（`opsx:apply` 済 / 必要なら `opsx:archive`）
- [ ] PR に Issue / Milestone / change / 検証結果を明記（AGENTS.md フロー8）

---

## 12. 差し戻し & 終了条件（無限ループ防止）

```
差し戻し上限 N = 2 （Orca circuit-break の 3 連続失敗より手前で人間へ）
```

- レビュー reject / 統合コンフリクト / 全体テスト失敗 → 元 Change を修正ループへ。回数をヘッダに刻む。
- **N 回超過 → human escalate**（gated は即停止、autonomous は `escalation` を上げて該当 Change を blocked にし、残りは続行）。

---

## 13. 周回クローズ & 再計画

```
[ ] この周回で完了した Issue: #__ #__
[ ] 残 Issue / 新規に割れた Change: ...
[ ] 次周回ヘッダを起こす（§1 に戻る）
```

Milestone 内 Issue が全て閉じるまで §1 へループ。**毎周 §0 の状態再導出から始める**（セッション断に強くするため、スケジューラ状態をメモリに溜めない）。

---

## 付録: ワンライン・チェックリスト（慣れたら本体はこれだけ）

```
状態再導出 → propose → self-grill(5a全/5b条件) → DAG(非交差&schema直列)
→ worktree dispatch(--inject) → worker_done待ち → マージ前レビュー(criticalは厚く)
→ 依存順統合 → ★統合後full test → Issue/PR反映 → N超過でescalate → 次周回
```
