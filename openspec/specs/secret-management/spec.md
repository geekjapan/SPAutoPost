# secret-management Specification

## Purpose
TBD - created by archiving change issue-4-initialize-application-skeleton. Update Purpose after archive.
## Requirements
### Requirement: Secret を repo に保存しない

システムは Secret（API key、token、credential、database URL の認証情報）をリポジトリに保存してはならない（SHALL NOT）。config file には実値ではなく `env:NAME` 形式の参照のみを記述しなければならない（SHALL）。

#### Scenario: config は env 参照のみ
- **WHEN** config file の Secret 項目を確認する
- **THEN** 値は `env:SPAUTOPOST_*` のような参照であり、実 Secret 値は含まれない

#### Scenario: サンプルにも実値を含めない
- **WHEN** `config.example.yml` を確認する
- **THEN** Secret 項目はすべて `env:NAME` 参照であり、ダミーの実 Secret 値も含まれない

### Requirement: 環境変数からの Secret 解決

システムは `env:NAME` 参照を起動時に対応する環境変数から解決しなければならない（SHALL）。環境変数の prefix は `SPAUTOPOST_` を推奨とする。

#### Scenario: 環境変数を解決
- **WHEN** `SPAUTOPOST_DATABASE_URL` が設定された状態で `env:SPAUTOPOST_DATABASE_URL` 参照を解決する
- **THEN** 環境変数の値が設定値として利用される

### Requirement: 必須 Secret の起動時検査

システムは起動時に、選択された構成で必要な Secret が設定されているか検査しなければならない（SHALL）。未設定の場合は validation error として停止しなければならない（SHALL）。

#### Scenario: 必須 Secret 未設定で停止
- **WHEN** 必須の `env:NAME` 参照に対応する環境変数が未設定のまま起動する
- **THEN** validation error として停止し、不足している変数名を示す（Secret 値そのものは表示しない）

### Requirement: log / エラー出力での Secret 秘匿

システムは log およびエラー出力に Secret 値を出力してはならない（SHALL NOT）。debug log でも Secret 値を秘匿（redaction）しなければならない（SHALL）。

#### Scenario: エラー出力に Secret を含めない
- **WHEN** Secret 解決に失敗してエラーを出力する
- **THEN** エラーメッセージは変数名のみを示し、解決済みまたは部分的な Secret 値を含まない

#### Scenario: debug log で redaction
- **WHEN** debug log レベルで設定をダンプする
- **THEN** Secret に該当する値は redaction 表示（例: `***`）となり、平文では出力されない

