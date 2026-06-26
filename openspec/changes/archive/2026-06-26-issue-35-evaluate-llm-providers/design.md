## Context

SPAutoPost M1 MVP は mock/template による DraftPost 生成を必須実装とする。一方、Issue #35 では任意 LLM provider の M1 投入可能性を評価する Spike を求めている。

現状:
- `docs/specs/llm-provider.md` — provider 分類・interface・audit 要件を定義済み（Status: Proposed）
- `docs/decisions/2026-06-22-llm-provider-strategy.md` — production/test 分離方針を決定済み（Status: Proposed）
- Issue #16 (Azure OpenAI), #17 (generic API) — 実装 Issue として存在するが着手前
- Issue #6 (mock provider) — M1 必須、interface 設計の基準となる

Spike の対象は「実装コードを書くか否かの判断」と「判断根拠の docs 記録」に限定する。M1 で着手しない場合は M3 の前提条件として Issue を更新する。

## Goals / Non-Goals

**Goals:**
- Azure OpenAI / Foundry provider を M1 に含めるか・M3 以降に先送りするかを判断する
- generic API provider（OpenAI-compatible）の M1 投入可能性を評価する
- test_manual provider の M1 における手動取込フローを明文化する
- provider interface（`DraftInput` / `DraftOutput` / error types / `ProviderMetadata`）の確定版を spec に反映する
- Spike 評価結果を `docs/specs/llm-provider.md` と ADR に記録し、後続 Issue (#16, #17) の判断根拠とする

**Non-Goals:**
- Azure OpenAI / Foundry / generic API provider の実装コード（src/ への追加なし）
- Chat UI の自動操作、UI scraping
- 本番環境での API 接続テスト
- provider コスト最適化
- 本番データ投入

## Decisions

### D1: M1 スコープ — Azure OpenAI / Foundry を含めない

**判断:** Azure OpenAI / Foundry provider (#16) および generic API provider (#17) は M1 に含めず M3 以降とする。

**理由:**
- M1 の完了条件は mock/template による DraftPost 生成であり、LLM API は必須でない
- Azure OpenAI / Foundry の利用条件・入力データ許容範囲・認証方式（Entra ID managed identity）の確認は M1 期間中に完了させる保証がない
- generic API（OpenAI-compatible）は利用条件が provider ごとに異なり、一般化 adapter の設計には interface 確定が先行必要
- Spike 期間中に API 接続テストを実施しない（本番データ不使用、環境未整備）

**代替案:** M1 に test 用 Azure OpenAI sandbox を含める → 認証セットアップのコスト・リスクが M1 の完了を遅らせる可能性があるため却下。

### D2: test_manual provider は M1 に含めるが自動化しない

**判断:** test_manual provider を M1 の optional 機能として位置づける。ChatGPT / Claude subscription での手動生成 → DraftPost への手動取込フローを spec に明文化する。

**理由:**
- 記事生成の実用感を M1 で確認するためには、手動評価が最小リスクかつ利用条件上安全
- UI 自動操作・API 非公式利用は禁止（ADR 確定済み）
- 手動取込フローの明文化は #6 (mock provider) の interface 設計と矛盾しない

### D3: Provider interface を M1 で確定する

**判断:** `docs/specs/llm-provider.md` の Provider interface（`generateDraft` / `validateConfig` / `getProviderMetadata` / `estimateCost`）を M1 で確定版とし、#6 (mock) の実装基準とする。

**理由:**
- interface が曖昧なまま mock を実装すると M3 で interface 破壊的変更が発生するリスクがある
- Spike 評価（Azure OpenAI / generic API の要件）を interface に反映してから mock を実装する順序が安全

### D4: docs のみ更新、src/ への変更なし

**判断:** この Spike タスクの成果物は docs/specs と docs/decisions の更新のみとし、実装コードは追加しない。

**理由:**
- Issue #35 のスコープは「評価」であり「実装」ではない
- M1 の完了条件（mock provider）は別 Issue (#6) で管理する

## Risks / Trade-offs

- [リスク] Azure OpenAI の利用条件・入力データ許容範囲が M3 時点で変更されている可能性 → Mitigation: M3 着手前に再確認ゲートを設ける（#16 に前提条件として記載）
- [リスク] generic API adapter の interface が Azure OpenAI と非互換になる可能性 → Mitigation: provider interface を抽象化して adapter ごとの差分を隠蔽する設計を spec に明示する
- [トレードオフ] M1 で LLM 品質を評価しないことで、M3 実装時に想定外の出力品質問題が発覚するリスク → test_manual の手動評価結果を記録することで緩和する

## Open Questions

- Azure OpenAI (Foundry) の入力データ許容範囲（社内の CVE 情報を投入してよいか）は情報セキュリティ部門の確認が必要 → M3 着手前のゲート条件とする
- generic API provider として優先する vendor（OpenAI API / Anthropic API / 他）は M3 設計時に決定する
