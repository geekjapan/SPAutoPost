## Context

`docs/specs/data-model.md` は Issue #28（storage baseline）以降の実装で既に参照されており、`docs/specs/audit-log.md`（event_type 15 値）や `openspec/specs/storage-schema` が data-model.md を normative に引いている。一方で `docs/specs/initial-system.md` の「Core Data Models」は AuditEvent を含まない旧来の軽量リストで、Advisory の出典表現も `source_*` フラットフィールドのままズレている。Issue #3 はこの概念モデルを M0 の Spec として正本化することが目的。

## Goals / Non-Goals

- **Goals**: 概念データモデルを OpenSpec capability `data-model` として固定する。出典→AI 生成→レビュー→投稿結果の end-to-end トレーサビリティ、publication の idempotency、AI 生成 provenance、collector 分離後の normalized advisory import を Spec レベルで保証する。
- **Non-Goals**: DB 製品選定、物理スキーマ／migration 設計（storage-* capability の領分）、フィールド型の言語別マッピング、ランタイム挙動。

## Decisions

- **正本の二層化**: 詳細フィールド一覧の正本は引き続き `docs/specs/data-model.md`（ナラティブ）。OpenSpec capability `data-model` は「何が必須で、何が追跡可能でなければならないか」を SHALL で固定し、data-model.md を normative reference として指す。フィールド表をプレーンテキストで二重管理して drift させない（DRY）。
- **initial-system.md は重複定義しない**: 実体を data-model.md に集約し、initial-system.md には正本ポインタと AuditEvent の所在のみ追記する。既存の `source_*` フラット記述は「概要レベルの旧表記」であり data-model.md の `source_refs` が正本である旨を注記する。
- **enum 値の正本は据え置き**: DraftStatus は data-model.md、AuditEvent.event_type（15 値）は `docs/specs/audit-log.md` を正本とする既存 reconcile note を維持。本 change では再定義しない。
- **SourceRecord / SourceRef / ReviewEvent も capability に含める**: Issue #3 の対象は Advisory/DraftPost/Publication/AuditEvent だが、出典トレーサビリティ（source reference）とレビュー追跡を成立させるには SourceRecord・SourceRef・ReviewEvent が必須要素のため requirement に含める。

## Risks / Trade-offs

- **二層正本の同期コスト**: data-model.md と capability requirement がズレる懸念。→ requirement はフィールド表を列挙せず「必須項目を持つこと」「追跡できること」を制約として書き、詳細は normative reference に委譲して同期点を最小化する。
- **storage baseline との縮退差**: data-model.md は `source_refs: SourceRef[]` を必須とするが storage baseline は単一 FK へ意図的に縮退済み（Issue #28 reconcile note）。単一 FK 実装は概念上「要素数 1 の `source_refs`」へ写像できる場合に限り、この capability へ適合する。複数情報源や per-source confidence が必要になった時点で、data-model.md の reconcile note 通り JSONB または junction table へ拡張する。本 change は物理スキーマを変更しない。

## Migration Plan

なし（Docs/Spec のみ、コード・データ変更なし）。archive 時に `data-model` capability が `openspec/specs/data-model/spec.md` として確定する。

## Open Questions

- data-model.md の Status を将来 `Proposed` → `Accepted` に昇格させるか。→ 本 change では据え置き（spec 群全体の status 運用方針が別途未確定のため）。
