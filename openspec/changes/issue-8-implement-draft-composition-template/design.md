## Context

既存コードには `DraftInput` / `DraftOutput` と外部通信しない `MockLLMProvider` がある。Issue #8 は本番 LLM 接続ではなく、SharePoint announcements 用の prompt / article template と guardrail を実装する範囲なので、既存 provider fallback の組み立て処理を template 化する。

## Goals / Non-Goals

**Goals:**

- Advisory から DraftOutput の title、summary_for_users、impact、required_actions、admin_actions、deadline、references を生成する。
- 出典リンクを DraftOutput に残す。
- 一般利用者向けと管理者向けの記述を分ける。
- 過剰断定と攻撃手順詳細化を避ける guardrail を prompt template / warnings / validation hints に残す。
- prompt version と input hash を記録する。

**Non-Goals:**

- 本番 LLM provider 接続。
- SharePoint HTML / web-part の最終 layout。
- 多言語対応。MVP は日本語 template のみ。

## Decisions

- `src/spautopost/llm/templates.py` に template 定数と `compose_sharepoint_draft()` を置く。新しい provider 抽象は作らず、既存 DTO をそのまま使う。
- `MockLLMProvider` の fixture 未指定 fallback は `compose_sharepoint_draft()` に委譲する。これにより Issue #6 の外部通信なし deterministic provider を保ったまま、Issue #8 の article template を通る。
- 入力 Advisory は `Mapping` または先頭要素を使う既存方針に合わせ、存在する field だけを短文に反映する。不明点は断定せず warnings / uncertainty_notes に出す。
- deadline は `deadline` / `due_date` / `recommended_deadline` 文字列が入力にあれば DraftOutput に保持し、なければ warning にする。

## Risks / Trade-offs

- 入力 schema がまだ最小なので文章は定型的になる → 本番 LLM provider が入るまで deterministic template として扱う。
- unsupported claim の自動検出は本 change の対象外 → 出典外断定を避ける文面と human review hint に留める。
