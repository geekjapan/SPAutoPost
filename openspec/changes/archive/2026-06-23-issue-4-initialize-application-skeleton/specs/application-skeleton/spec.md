## ADDED Requirements

### Requirement: Repository レイアウト

システムは Python アプリケーションの最小レイアウトを提供しなければならない（SHALL）。アプリケーションコードは `src/spautopost/` 配下に置き、テストは `tests/` に `src/` と対応する構造で配置しなければならない（SHALL）。

#### Scenario: src レイアウトが存在する
- **WHEN** リポジトリを clone して構造を確認する
- **THEN** `src/spautopost/` にパッケージ（`__init__.py` を含む）と `tests/` ディレクトリが存在する

#### Scenario: パッケージが import 可能
- **WHEN** 開発環境で `spautopost` パッケージを import する
- **THEN** ImportError なく読み込め、バージョン情報を取得できる

### Requirement: CLI / batch entrypoint

システムは単一の CLI / batch entrypoint を提供しなければならない（SHALL）。この entrypoint は最終運用形ではなく、Azure Container Apps Jobs の command entrypoint として将来利用できる形で設計しなければならない（SHALL）。

#### Scenario: CLI を help 付きで起動できる
- **WHEN** ユーザーが entrypoint を `--help` 付きで実行する
- **THEN** 利用可能なサブコマンドと dry-run / 環境指定オプションを含む usage が表示され、終了コード 0 を返す

#### Scenario: 環境別 config を指定して起動できる
- **WHEN** ユーザーが環境（例: development）を指定して entrypoint を実行する
- **THEN** 対応する config が読み込まれ、起動シーケンスが開始される

### Requirement: 起動シーケンス

システムは起動時に「config 読み込み → validation → command dispatch」の順で処理しなければならない（SHALL）。validation に失敗した場合はコマンドを実行せず、非ゼロ終了コードで停止しなければならない（SHALL）。

#### Scenario: 正常起動
- **WHEN** 妥当な config と必須 Secret が揃った状態で起動する
- **THEN** config load と validation を通過し、指定されたコマンドが dispatch される

#### Scenario: validation 失敗で停止
- **WHEN** config が不正、または必須 Secret が未設定の状態で起動する
- **THEN** コマンドを dispatch せず、エラー要約を出力して非ゼロ終了コードで停止する

### Requirement: 起動方法のドキュメント

システムは README または docs に起動方法を記載しなければならない（SHALL）。記載には CLI 実行、dry-run の使い方、環境別 config の指定方法を含めなければならない（SHALL）。

#### Scenario: README に起動手順がある
- **WHEN** 新規開発者が README を参照する
- **THEN** CLI 実行コマンド、dry-run の指定、環境別 config の指定方法が記載されている
