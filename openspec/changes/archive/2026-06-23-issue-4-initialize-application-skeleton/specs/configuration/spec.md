## ADDED Requirements

### Requirement: 環境分離された config file schema

システムは環境ごとに分離した config file を読み込めなければならない（SHALL）。`config/default.yml` を基底とし、環境別ファイル（development / test / production）で上書きできなければならない（SHALL）。実 config は gitignore し、リポジトリには `config.example.yml` を提供しなければならない（SHALL）。

#### Scenario: 環境別 config の上書き
- **WHEN** development 環境で起動する
- **THEN** `config/default.yml` の値が `config/development.yml` の値で上書きされた設定が適用される

#### Scenario: サンプル config が提供される
- **WHEN** リポジトリを確認する
- **THEN** `config.example.yml` が存在し、実 config（`config/*.yml`）は gitignore されている

### Requirement: provider / source / 投稿先の切替設定

システムは LLM provider、source adapter、SharePoint 投稿先、storage provider を config で切り替え可能にしなければならない（SHALL）。

#### Scenario: provider を設定で選択
- **WHEN** config の `llm.provider` を `mock` に設定して起動する
- **THEN** 選択された provider が解決され、未知の値の場合は validation error となる

#### Scenario: storage provider を設定で選択
- **WHEN** config の `storage.provider` を `postgresql` または `sqlite` に設定する
- **THEN** 選択値が検証され、対応する接続設定（database_url / sqlite_path）が要求される

### Requirement: dry-run 既定

システムは `dry_run` を既定で true としなければならない（SHALL）。`dry_run: true` のとき、SharePoint への投稿を行ってはならない（SHALL NOT）。

#### Scenario: dry-run が既定で有効
- **WHEN** `dry_run` を明示しない config で起動する
- **THEN** dry-run が有効として扱われ、外部投稿を伴う操作は preview に留まる

#### Scenario: dry-run では投稿しない
- **WHEN** `dry_run: true` で publish 系コマンドを実行する
- **THEN** SharePoint へ投稿せず、publish payload の preview を出力する

### Requirement: 起動時 config validation

システムは起動時に config を検査しなければならない（SHALL）。少なくとも environment、storage provider と接続設定、provider 選択、SharePoint mode と必須 target ID、`allow_publish` と `require_approval` の整合、Secret 参照の存在、未知の config key を検査しなければならない（SHALL）。未知の config key を検出した場合はエラーとしなければならない（SHALL）。

#### Scenario: 必須項目欠如で失敗
- **WHEN** 必須の storage 接続設定が欠けた config で起動する
- **THEN** validation error を返し、何が不足しているかを示す（Secret 値は含めない）

#### Scenario: 未知の key を拒否
- **WHEN** config に未知の key が含まれた状態で起動する
- **THEN** validation error として停止する
