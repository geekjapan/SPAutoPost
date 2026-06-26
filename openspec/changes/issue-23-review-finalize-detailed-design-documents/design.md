## Context

Issue #23 の対象文書は、SharePoint 投稿、data model、LLM provider、draft composition、collection、normalization、review / approval、audit、security、configuration、error handling、external collector boundary、runbook、ADR にまたがる。各文書には Status があるが、M0 完了判断に必要な「Accepted / near-Accepted」「M1+ deferred」「未決事項の集約先」が中央化されていない。

AGENTS.md は GitHub Issue を正本とし、仕様不足を推測で埋めないことを要求している。したがって、この change は文書分類と routing だけを行い、#2 と #15 の判断を先取りしない。

## Goals / Non-Goals

**Goals:**

- Issue #23 対象文書を 1 つの review matrix で一覧できるようにする。
- M0 で Accepted / near-Accepted と扱う文書と、M1 以降で確定する文書を明示する。
- SharePoint publishing / board contract の未決事項を #2 に route する。
- LLM provider strategy の未決事項を #15 に route する。
- 実装先行の spec gap がある場合、既存 Issue にだけ紐づける。

**Non-Goals:**

- SharePoint 投稿方式、Graph permission、publish / promote lifecycle を決定しない。
- LLM production provider、test provider、契約、入力データ制限を決定しない。
- runtime code、migration、auth、Secret、external service、Azure resource、SharePoint publish behavior を変更しない。
- speculative follow-up Issue を作成しない。

## Decisions

1. Matrix は `docs/design-documents.md` に置く。
   - 既存の設計文書 index であり、実装エージェントの reading order にも含まれるため。
   - 別ファイルを増やすより、Issue #23 の目的に対して最小差分で済む。

2. 文書自体の Status は原則変えず、Issue #23 review result を別列で示す。
   - Proposed 文書でも M0 near-Accepted として扱えるものがあるため、元 Status を上書きすると誤解を招く。
   - 後続 Milestone で確定する文書は deferred milestone / routed issue で表現する。

3. Unresolved decisions は既存 Issue へ route し、新規 Issue は作らない。
   - #2 が SharePoint board contract、#15 が LLM provider strategy を既に正本として持つ。
   - Issue #23 は docs review であり、未決事項を決定する change ではない。

## Risks / Trade-offs

- Matrix が古くなる → 各行に authoritative follow-up Issue を置き、変更時の更新先を明確にする。
- Status と review result が二重管理になる → Status は文書自身の採用状態、review result は Issue #23 の整理結果として役割を分ける。
- 実装先行 gap を過剰に増やす → 既存 Issue で明確に追跡できるものだけを書く。
