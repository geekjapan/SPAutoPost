## Why

Issue / OpenSpec change 駆動で実装を始めるには、最小のアプリケーション骨格・設定方針・Secret 参照方針が必要だが、現状 `src/` もエントリポイントも config schema も存在しない。後続の M1 Issue（#6 LLM provider、#9 SharePoint PoC、#10 dry-run/audit、#28 PostgreSQL）はいずれも「設定で provider/source/投稿先を切り替えられ、dry-run を既定にでき、Secret を repo に置かない」基盤に依存するため、最初にこの土台を確定する。

本 change は Issue #4（M0: Project Foundation）に対応し、`docs/specs/configuration.md` と `docs/decisions/2026-06-22-mvp-runtime-and-language.md`（core=Python、最小実装単位=CLI/Batch）を正本として、その方針を OpenSpec capability に落とし込む。

## What Changes

- Python の最小アプリケーション骨格を導入する（`src/` レイアウト、CLI / batch entrypoint、起動時の config 読み込み・validation）。CLI は最終運用形ではなく Azure Container Apps Jobs の command entrypoint として設計する。
- 環境分離された config file schema を定義する（`config/default.yml` ほか、実 config は gitignore、`config.example.yml` を提供）。
- `dry_run` を既定 true とし、provider（LLM）・source adapter・SharePoint 投稿先・storage provider を設定で切り替え可能にする。
- Secret 参照方針を確立する（config には `env:NAME` 参照のみ。起動時に未設定なら validation error。エラー・log に Secret 値を出さない）。
- README / docs に起動方法（CLI 実行、dry-run、環境別 config 指定）を記載する。
- **非対象**: 実 API 呼び出し実装、本番 Secret 投入、CI/CD 本格構築、PostgreSQL 実接続（schema 検証はダミー/SQLite で代替可）。

## Capabilities

### New Capabilities

- `application-skeleton`: Python の repository レイアウト（`src/` / `tests/`）、CLI / batch entrypoint、起動シーケンス（config load → validation → command dispatch）、README 起動手順。
- `configuration`: 環境分離 config file schema、`env:NAME` Secret 参照、provider / source / SharePoint / storage の選択設定、`dry_run` 既定値、起動時 config validation、`config.example.yml`。
- `secret-management`: Secret を repo に保存しない方針、`env:NAME` 解決、起動時の必須 Secret 存在検査、log / エラー出力での Secret 秘匿（redaction）。

### Modified Capabilities

<!-- openspec/specs/ は空（既存 OpenSpec capability なし）。docs/specs/ は設計ノートであり OpenSpec spec ではないため、本 change は新規 capability のみ。 -->

## Impact

- **新規コード**: `src/spautopost/`（CLI entrypoint、config loader/validator、secret resolver）、`tests/`、`config.example.yml`、`config/`（gitignore 対象）。
- **依存関係**: `pyproject.toml` に `[project]` / `[build-system]` と最小依存（YAML parser、CLI framework、設定 validation）を追加予定。現状は `[tool.*]` のみ。
- **ドキュメント**: README に起動方法を追記。`docs/specs/configuration.md` を正本として参照（重複定義はしない）。
- **既存仕様との整合**: `docs/specs/architecture.md` を MVP アーキの正本として尊重。Secret/認証/publish には触れない（人間ゲート対象のため本 change のスコープ外）。
- **非対象による制約**: 実 provider 呼び出し・PostgreSQL 実接続・CI は別 Issue（#6/#9/#28 ほか）。
