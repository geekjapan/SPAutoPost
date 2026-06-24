## Why

M1 Phase 2 needs a manual / fixture path that can create normalized `Advisory` data before automatic collectors exist. Issue #7 requires YAML / JSON input, validation, samples, invalid-input tests, and a dry-run preview while explicitly excluding NVD / MyJVN API and crawler behavior.

## What Changes

- Add a manual advisory input capability for YAML / JSON files.
- Validate required fields, CVE ID, JVN ID, URL, references, severity, and urgency.
- Convert valid manual input into the existing Python `Advisory` DTO.
- Add sample advisory files under `samples/advisories/`.
- Add a CLI `import-advisory` dry-run preview that reads and displays the normalized result without posting or calling external APIs.
- **非対象**: NVD / MyJVN API 接続、crawler 実装、社内資産台帳連携、DraftPost 生成、SharePoint 投稿。

## Capabilities

### New Capabilities

- `manual-advisory-input`: YAML / JSON の手動入力を検証し、既存の `Advisory` model に変換する。

### Modified Capabilities

<!-- 既存 OpenSpec capability の requirement は変更しない。 -->

## Impact

- **新規コード**: `src/spautopost/advisory_input.py`
- **CLI**: `spautopost import-advisory <file>` を追加する。
- **テスト**: valid input / invalid input / CLI dry-run preview を追加する。
- **サンプル**: `samples/advisories/` に YAML / JSON fixture を追加する。
- **依存関係**: 追加なし。既存の `pyyaml` と Python stdlib を使う。
- **セキュリティ**: 外部 API 呼び出し、投稿、Secret 保存は行わない。
