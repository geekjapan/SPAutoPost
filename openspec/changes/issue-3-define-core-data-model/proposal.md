## Why

M0 では、脆弱性情報の収集元・AI 作文・SharePoint 投稿を疎結合に保つための共通データモデルが必要（Issue #3）。`docs/specs/data-model.md` は既に Advisory / DraftPost / Publication / AuditEvent を記述しているが、OpenSpec capability として正本化されていないため、後続実装（storage baseline, draft composition, publish）の参照点が散在している。本 change は概念データモデルを `data-model` capability として正本化し、出典・AI 生成・レビュー・投稿結果の追跡可能性と、external collector 分離後も使える input model を Spec レベルで固定する。

## What Changes

- `data-model` capability を新設し、主要エンティティと必須項目、トレーサビリティ、idempotency、provenance、collector 分離後 input model を requirement として定義する。
- 正本ナラティブは `docs/specs/data-model.md`（既存）とし、capability requirement はそこを normative reference として参照する。
- `docs/specs/initial-system.md` の「Core Data Models」に、`data-model.md` を正本とする旨と AuditEvent の所在を示す cross-reference を追記する（実体の重複定義はしない）。
- **非対象**: DB 製品選定、本格的なマイグレーション設計、ランタイムコード・migration・secrets・auth・外部 API・Azure・SharePoint・投稿挙動の変更。

## Capabilities

### New Capabilities

- `data-model`: SPAutoPost の正規化済み概念データモデル（SourceRecord / Advisory / DraftPost / ReviewEvent / Publication / AuditEvent）と、出典〜投稿結果の追跡可能性・idempotency・AI 生成 provenance・collector 分離後 input model を定義する。

### Modified Capabilities

<!-- 既存 OpenSpec capability の requirement は変更しない。 -->

## Impact

- **Docs/Spec のみ**: コード・migration・設定の変更なし。
- **正本ナラティブ**: `docs/specs/data-model.md`（既存、変更なし、normative reference として引用）。
- **更新**: `docs/specs/initial-system.md` に cross-reference を追記。
- **依存関係**: 追加なし。
- **セキュリティ**: データモデルに Secret を保存しない方針を requirement として固定（既存 `data-model.md` の Sensitive Data Policy を正本化）。
