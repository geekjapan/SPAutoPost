## Why

Issue #33 では、M1 の Python core source and draft pipeline として、手動入力以外の最小 source job から投稿候補を作り、Advisory と DraftPost 生成へ接続する必要がある。
本格 crawler や外部 API ではなく、保存・生成・scheduled job skeleton の縦串確認を優先する。

## What Changes

- 外部通信しない deterministic sample source から投稿候補を取得する。
- sample source metadata を `SourceRecord` に保持し、候補を既存 `Advisory` DTO に変換する。
- 既存 `StoragePort` を通じて `SourceRecord`、`Advisory`、`DraftPost` を保存する。
- 既存 mock/template draft generation へ `Advisory` を渡し、`DraftPost` を生成する。
- scheduled job skeleton から呼び出せる Python 関数と CLI command を追加する。
- 本格 crawler、高精度 dedupe、実外部 API、SharePoint publish、認証・Secret 操作は追加しない。

## Capabilities

### New Capabilities

- `sample-source-job`: deterministic sample source から source metadata、Advisory、DraftPost を生成・保存する M1 用 job を扱う。

### Modified Capabilities

- なし。

## Impact

- `src/spautopost/`
- `tests/`
- `README.md`
- `openspec/changes/issue-33-implement-sample-source-job/`
