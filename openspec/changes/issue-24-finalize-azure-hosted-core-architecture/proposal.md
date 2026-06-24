## Why

SPAutoPost の主要ユースケースは、定期収集 → 記事生成 → 管理者確認・確定 → SharePoint Site Page / News 投稿である。この運用コアを人間ユーザーの端末に依存させず、Azure 上の常時起動 / 定期起動できる container runtime に据える方針を確定し、M1 実装 Issue（#25 deployment skeleton ほか）に落とせる状態にする（Issue #24, M0）。

既存の `docs/specs/architecture.md`・`docs/decisions/2026-06-22-azure-hosted-core.md`・`docs/specs/deployment.md` は方針をほぼ反映済みのため、本 change はそれらを正本として参照する binding な architecture policy capability を OpenSpec 上に固定し、未決事項（storage / identity / logging）の Issue 追跡を明示する。docs は不足分のみ最小差分で補足する。

## What Changes

- 新 capability `azure-hosted-core` を追加し、Azure hosted core architecture の binding な不変条件を OpenSpec 上に固定する。
- 「定期収集・投稿処理の運用コアをユーザー端末に依存させない」ことを requirement として明文化する。
- CLI / Batch を Container Apps Jobs の command entrypoint と dev / dry-run / 手動再実行 / 障害補助に限定し、運用コアそのものではないことを明文化する。
- M1 で実装すべき deployment skeleton の範囲（Container Apps Admin UI/API、Container Apps Jobs、PostgreSQL、env vars、container build、GitHub Actions skeleton、Bicep skeleton）を requirement に固定する。
- storage / identity / logging の未決事項が GitHub Issue で追跡されていること（#28 storage、#27 / #29 / #32 identity、#30 logging）を requirement として固定する。
- docs 補足（最小差分）: `architecture.md` に未決事項の Issue リンク（特に logging #30、identity #32）と Issue #24 受け入れ note を追記する。ADR / deployment.md は既に条件を満たすため、必要時のみ Related Issue を補う。
- **非対象**: Azure リソースの本番作成、本番 Secret 登録、本格管理 UI 実装、本番 DB 完全確定、auth / publish コードの変更、実 IaC / Bicep 実装。

## Capabilities

### New Capabilities

- `azure-hosted-core`: SPAutoPost の運用コアを Azure container runtime に据え、ユーザー端末を運用コアにしない architecture policy を binding に固定し、M1 deployment skeleton 範囲と未決事項の Issue 追跡を規定する。

### Modified Capabilities

<!-- 既存 OpenSpec capability の requirement は変更しない。 -->

## Impact

- **ドキュメント**: `docs/specs/architecture.md` に未決事項 Issue リンクと受け入れ note を最小差分で追記する。`docs/decisions/2026-06-22-azure-hosted-core.md`（既に Accepted）・`docs/specs/deployment.md` は必要時のみ Related Issue を補う。
- **コード**: 変更なし（docs / spec finalization のみ）。
- **テスト**: 変更なし。`openspec validate --strict` を検証手段とする。
- **依存関係**: 追加なし。
- **セキュリティ**: Azure リソース作成・Secret 登録・auth / publish コード変更は行わない。Secret を docs / spec / fixture に記載しない。
