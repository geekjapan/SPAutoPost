## Context

GitHub Issue #7 は、collector 実装前に手動入力または fixture から脆弱性情報を取り込めることを求めている。既存コードには `storage.models.Advisory` DTO と CLI / config / dry-run の骨格があるため、新しい永続化 model や外部 adapter interface は不要。

## Goals / Non-Goals

**Goals:**

- YAML / JSON ファイルを読み込み、既存 `Advisory` DTO に変換する。
- required fields、CVE ID、JVN ID、URL、severity、urgency、references を検証する。
- `import-advisory` コマンドで dry-run preview を表示する。
- invalid input の unit test とサンプル advisory を追加する。

**Non-Goals:**

- NVD / MyJVN / vendor API への接続。
- crawler / scheduler / source fetch state。
- DraftPost 生成、保存、SharePoint 投稿。
- Issue #6 の LLM provider 動作。

## Decisions

- **手動入力専用 module を追加する**: `src/spautopost/advisory_input.py` に parse / validate / convert を閉じ込める。CLI に validation 文字列を散らさず、後続の sample source job からも再利用できる。
- **既存 DTO を使う**: `Advisory` にない `urgency` は downstream hint として validation / preview までに留め、data model を拡張しない。Issue #7 は DraftPost 生成を対象外としているため。
- **依存を増やさない**: YAML / JSON は既存依存の `pyyaml` で読み、URL / ID validation は stdlib (`urllib.parse`, `re`) で行う。
- **dry-run は preview のみ**: `import-advisory` は外部 API・投稿・永続化をしない。dry-run 時は JSON preview に `dry_run: true` を出す。

## Risks / Trade-offs

- [JVN ID 形式の網羅性] → Issue #7 の最低限 validation として `JVN#...` / `JVNVU#...` / `JVNDB-YYYY-NNNNNN` を許可する。必要なら MyJVN adapter 実装時に拡張する。
- [SourceRecord 生成なし] → Issue #7 は Advisory 生成が完了条件であり、永続化や fetch audit は #10 / source adapter 系に委譲する。
- [config validation が import 前に走る] → 既存 CLI の起動順序（config load → validation → dispatch）を維持する。

## Migration Plan

DB migration は不要。CLI command と sample files の追加のみ。

## Open Questions

なし。Issue #7 の範囲内で実装可能。
