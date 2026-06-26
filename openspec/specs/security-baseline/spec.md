# security-baseline Specification

## Purpose
TBD - created by archiving change issue-5-security-secrets-audit-baseline. Update Purpose after archive.
## Requirements
### Requirement: Secret を保存・出力してはならない
システムは、API key・access token・refresh token・client secret・certificate private key・cookie・authorization header をソースコード・設定ファイル・テストフィクスチャ・ログ・例外メッセージに含めてはならない（SHALL NOT）。

#### Scenario: Secret のコミット防止
- **WHEN** CI パイプラインがコードを検査する
- **THEN** Secret スキャンツールが Secret の混入を検出し、マージをブロックする

#### Scenario: ログへの Secret 出力防止
- **WHEN** アプリケーションが任意のログを出力する
- **THEN** ログに API key・token・secret が含まれていないこと

### Requirement: Secret は環境変数または secret store から参照する
システムは、Secret を environment variable・GitHub Actions secrets・Azure Key Vault・managed identity のいずれかの方式でのみ参照しなければならない（SHALL）。`.env` ファイルはコミット対象外とする。

#### Scenario: 起動時の Secret 存在確認
- **WHEN** アプリケーションが起動する
- **THEN** 必須 Secret がすべて設定されているか検証し、不足する場合はエラーで終了する

### Requirement: Microsoft Graph 権限は最小限にする
システムは、投稿対象 SharePoint site / list / page に必要な権限のみを付与しなければならない（SHALL）。tenant 全体権限は避ける。本番用と開発用の app registration を分離する。

#### Scenario: 権限の documentation 記録
- **WHEN** Graph 権限を設定する
- **THEN** 付与した permission と採用方式（delegated / application）が decision record または runbook に記録されている

### Requirement: LLM provider に渡す情報を最小化する
システムは、Secret・個人情報・社内ネットワーク構成・内部 IP / hostname・認証方式の詳細・未公開インシデント情報・攻撃者に有益な内部防御状況を LLM provider に送信してはならない（SHALL NOT）。

#### Scenario: LLM 入力の禁止情報チェック
- **WHEN** LLM provider へのリクエストを組み立てる
- **THEN** prompt に Secret・個人情報・内部ネットワーク情報が含まれていないこと

### Requirement: AI 出力を人間レビューなしに自動公開してはならない
システムは、approved でない DraftPost を SharePoint に publish してはならない（SHALL NOT）。LLM 出力は必ず人間レビューフローを経由してから公開される。

#### Scenario: 未承認 DraftPost の公開拒否
- **WHEN** DraftPost のステータスが approved でない状態で publish が試みられる
- **THEN** システムはエラーを返し、SharePoint への投稿を行わない

#### Scenario: 承認済み DraftPost の公開許可
- **WHEN** DraftPost のステータスが approved である
- **THEN** システムは SharePoint への投稿を実行できる

### Requirement: AI 出力安全性を保証する
システムが生成する SharePoint 投稿原稿は、出典にない事実を断定しないこと・攻撃手順または PoC を含まないこと・不確実な事項を不確実と示すことを満たさなければならない（SHALL）。

#### Scenario: 出典根拠チェック
- **WHEN** AI が原稿を生成する
- **THEN** 原稿に含まれる事実は収集した advisory または公開情報に基づいている

### Requirement: 投稿先を固定する
システムは、config で指定した SharePoint site / list / page 以外への投稿を拒否しなければならない（SHALL）。任意 URL への投稿は禁止する。dry-run モードを提供する。

#### Scenario: 任意 URL 投稿拒否
- **WHEN** 設定外の URL への投稿が試みられる
- **THEN** システムはエラーを返し、投稿を行わない

#### Scenario: dry-run 実行
- **WHEN** dry-run モードで実行する
- **THEN** SharePoint への実投稿なしに投稿内容の検証のみが行われる

### Requirement: 重複投稿を防ぐ
システムは、idempotency_key を用いて同一 DraftPost の二重投稿を防止しなければならない（SHALL）。

#### Scenario: 重複投稿の検出と防止
- **WHEN** 同一 idempotency_key で publish が二回目に試みられる
- **THEN** システムは重複を検出し、二度目の投稿を行わない

