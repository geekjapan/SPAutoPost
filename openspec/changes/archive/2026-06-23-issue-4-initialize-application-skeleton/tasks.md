## 1. パッケージング基盤

- [x] 1.1 `pyproject.toml` に `[project]`（name/version/python>=3.12）と `[build-system]` を追加する
- [x] 1.2 最小依存（YAML parser、config validator）を Research & Reuse ゲートで選定し追記する
- [x] 1.3 `.gitignore` に `config/*.yml`（example 除く）・生成キャッシュを追加する

## 2. Repository 骨格

- [x] 2.1 `src/spautopost/__init__.py`（バージョン情報含む）を作成する
- [x] 2.2 `tests/` を `src/` 対応構造で用意する
- [x] 2.3 パッケージが import 可能なことをテストで確認する（RED→GREEN）

## 3. config loader / validation

- [x] 3.1 `default.yml` → 環境別 → 環境変数解決の順でマージする loader を実装する
- [x] 3.2 起動時 validation（environment / storage provider と接続設定 / provider 選択 / SharePoint mode と必須 target ID / allow_publish と require_approval の整合 / Secret 参照存在 / 未知 key 拒否）を実装する
- [x] 3.3 validation 失敗時に非ゼロ終了・不足項目提示（Secret 値は出さない）をテストで確認する

## 4. Secret 解決 / 秘匿

- [x] 4.1 `env:NAME` を環境変数へ解決する単一 resolver を実装する
- [x] 4.2 必須 Secret 未設定時に validation error（変数名のみ提示）とする
- [x] 4.3 設定ダンプ・エラー・debug log で Secret を redaction（`***`）し、平文が出ないことをテストで確認する

## 5. CLI / batch entrypoint

- [x] 5.1 単一 entrypoint と `--help`・環境指定・dry-run オプションを実装する
- [x] 5.2 起動シーケンス（config load → validation → command dispatch）を実装する
- [x] 5.3 `validate-config` サブコマンドを実装する
- [x] 5.4 dry-run 既定（`dry_run: true`）で publish 系は preview に留めることを実装・テストする

## 6. サンプル設定とドキュメント

- [x] 6.1 `config.example.yml`（Secret はすべて `env:NAME` 参照、実値なし）を作成する
- [x] 6.2 README に起動方法（CLI 実行・dry-run・環境別 config 指定）を追記する

## 7. 検証

- [x] 7.1 ローカルで ruff / mypy / pytest（カバレッジ 80%+）を通す
- [x] 7.2 `openspec validate issue-4-initialize-application-skeleton --strict` を通す
- [x] 7.3 Issue #4 の受け入れ条件（CLI entrypoint / sample config / Secret 非保存方針 / dry-run・provider 切替 / 起動方法ドキュメント）を満たすことを確認する
