## Context

SPAutoPost は GitHub 駆動・仕様駆動で、core language は Python、最小実装単位は CLI / Batch command（`docs/decisions/2026-06-22-mvp-runtime-and-language.md`）。現状 `src/` もエントリポイントも config schema も無く、`pyproject.toml` は `[tool.*]` のみ（`[project]` / `[build-system]` 未定義）。`docs/specs/configuration.md` が config・Secret・dry-run・provider 切替の方針を既に定めており、本 change はそれを OpenSpec capability と最小骨格に落とす。本 change の depth は「骨格と設定方針の確定」であり、実 provider 呼び出し・PostgreSQL 実接続・CI は対象外。

## Goals / Non-Goals

**Goals:**
- Python の `src/` レイアウトと単一 CLI / batch entrypoint を確立する。
- 環境分離 config schema、`env:NAME` Secret 参照、起動時 validation、dry-run 既定を実装可能な形で定義する。
- `config.example.yml` と README 起動手順を用意する。
- 後続 Issue（#6/#9/#10/#28）が依存する設定・provider 切替・dry-run の土台を提供する。

**Non-Goals:**
- 実 LLM / Graph / SharePoint API 呼び出し（#6/#9/#32/#36）。
- PostgreSQL 実接続・migration（#28）。SQLite/ダミーで schema 形だけ確認可。
- 認証・認可・Secret 投入・publish の実行（人間ゲート対象）。
- CI/CD の本格構築。

## Decisions

- **CLI framework**: 標準 `argparse` を第一候補とし、サブコマンド構造（例: `validate-config`, `dry-run`）を取る。理由: 依存最小・Azure Jobs entrypoint として軽量。代替（Typer/Click）は表現力が高いが MVP 骨格には過剰。導入時に Research & Reuse ゲートで再評価する。
- **config loader**: YAML を `default.yml` → 環境別 → 環境変数解決の順でマージ。schema validation は宣言的バリデータ（例: Pydantic）を候補とする。理由: `docs/specs/configuration.md` の検査項目（未知 key 拒否、整合検査）を型で表現でき、Secret redaction を一箇所に集約できる。代替（手書き dict 検査）は DRY/網羅性で劣る。
- **Secret 解決**: config 内 `env:NAME` を loader が環境変数へ解決する単一の resolver に集約。redaction も同 resolver が担い、設定ダンプ時は Secret 由来フィールドを `***` 化。理由: 漏洩面を一点に閉じ込める。
- **dry-run 既定**: config 既定値で `dry_run: true`。publish 系コードパスは dry-run 時に preview のみ。理由: 事故防止（publish は人間ゲート）。
- **gitignore 方針**: `config/*.yml`（example を除く）と生成キャッシュをコミット対象外にする。

## Risks / Trade-offs

- [新規依存（YAML/validator）の選定が後続に影響] → 依存は最小に絞り、`pyproject.toml` の `[project]` 追加時に Research & Reuse ゲートを通す。本 change では候補提示に留め、確定は実装フェーズ。
- [config schema を先に固めすぎると後続 Issue で手戻り] → 本 change は #4 受け入れ条件に必要な範囲（骨格・dry-run・provider 切替・Secret 方針）に限定し、provider 固有 schema は各 Issue へ委譲。
- [Secret 秘匿の取りこぼし] → redaction を resolver に集約し、テストで「設定ダンプに平文 Secret が出ない」ことを検証する。
- [CI 未整備のため自動検証が弱い] → 当面は手動テスト＋ローカル ruff/mypy/pytest。auto-merge ではなく人間レビューにフォールバック（AGENTS.md の carve-out）。

## Migration Plan

新規追加のみで既存実装は無いため migration は不要。導入手順: `[project]`/`[build-system]` 追加 → `src/spautopost/` 骨格 → config loader/validator/secret resolver → `config.example.yml` → README 起動手順 → tests。ロールバックはコミット revert で完結。

## Open Questions

- CLI framework と validator（argparse+Pydantic か否か）の最終確定は実装フェーズで Research & Reuse ゲートにかける。
- `pyproject.toml` の最小依存セットの確定（YAML parser の選定含む）。
- provider/source の plug-in 解決方式（entry points か単純 registry か）は本 change では未確定。後続 #6 等と整合して決める。
