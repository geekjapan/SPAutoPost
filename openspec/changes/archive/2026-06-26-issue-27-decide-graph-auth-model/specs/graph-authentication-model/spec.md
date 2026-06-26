## ADDED Requirements

### Requirement: local PoC 認証方式の決定
local PoC / 初期疎通では、Microsoft Graph への認証に delegated permission（Device Code Flow）を使用しなければならない（SHALL）。ユーザーの端末でブラウザ認証を完了し、取得したトークンで Graph を呼び出す。Secret は repo にコミットしてはならない（SHALL NOT）。

#### Scenario: local PoC での Graph 呼び出し
- **WHEN** 開発者が local 環境で `spautopost` CLI を実行し Device Code Flow で認証する
- **THEN** Microsoft Graph が delegated permission でアクセス可能になり、SharePoint Site Page の作成・更新操作が成功する

#### Scenario: local PoC での Secret 非保存
- **WHEN** 認証フローが完了しトークンが発行される
- **THEN** refresh token / access token はメモリまたは OS 標準の token cache にのみ保持され、repo ファイルには書き込まれない

### Requirement: Azure hosted runtime 認証方式の決定
Azure Container Apps / Azure Container Apps Jobs 上で動作する SPAutoPost の実行環境では、user-assigned managed identity を第一候補として使用しなければならない（SHALL）。managed identity で対応できない制約がある場合に限り、application permission / app-only access（client secret または certificate）を fallback として使用してよい（MAY）。

#### Scenario: managed identity による Graph 呼び出し
- **WHEN** Azure Container Apps Jobs が定期実行として起動する
- **THEN** user-assigned managed identity の credential で Microsoft Graph の認証が成功し、SharePoint Site Page を作成・更新できる

#### Scenario: fallback として app-only access を使用する条件
- **WHEN** managed identity への Graph permission 付与が技術的・組織的制約により不可能であると M1 検証で確認された場合
- **THEN** application permission / app-only access（client credentials flow）を使用し、Secret は Azure Key Vault に保管する

### Requirement: managed identity 採否の決定
SPAutoPost は user-assigned managed identity を Azure hosted runtime の identity として採用しなければならない（SHALL）。Container Apps App と Container Apps Jobs で同一の user-assigned managed identity を共有する。system-assigned managed identity は使用しない（SHALL NOT）。

#### Scenario: Container Apps App と Jobs 間での identity 共有
- **WHEN** Container Apps App と Container Apps Jobs が同一 user-assigned managed identity を使用するよう設定される
- **THEN** 両リソースが同じ Graph permission セットで動作し、identity 管理が一元化される

#### Scenario: Secret なし運用の確認
- **WHEN** managed identity を使用する Azure hosted runtime が起動する
- **THEN** client secret および certificate private key なしで Graph 認証が成功する

### Requirement: delegated permission を本番定期実行に使わないことの明記
Azure hosted runtime の定期実行ジョブ（Azure Container Apps Jobs）では、delegated permission を本番の主要認証方式として使用してはならない（SHALL NOT）。ユーザーの常時ログイン状態やブラウザセッションに依存する認証は本番定期実行に採用しない（SHALL NOT）。

#### Scenario: 本番定期実行での delegated permission 不使用
- **WHEN** Azure Container Apps Jobs が unattended（非対話型）で定期実行される
- **THEN** 認証は managed identity または app-only access によって完結し、ユーザーのセッション状態を参照しない

### Requirement: Graph permission 最小化方針
SPAutoPost に付与する Microsoft Graph permission は、SharePoint Site Page / News 投稿に必要な最小セットに限定しなければならない（SHALL）。`Sites.Selected` permission を優先して使用し、`Sites.ReadWrite.All` 等の広範な permission は避けなければならない（SHALL）。

#### Scenario: Sites.Selected の使用
- **WHEN** app registration または managed identity に Graph permission を付与する
- **THEN** `Sites.Selected` を使用し、投稿対象の SharePoint site のみにアクセス権を限定する

#### Scenario: 広範 permission の禁止
- **WHEN** Graph permission セットをレビューする
- **THEN** `Sites.ReadWrite.All`、`Sites.FullControl.All` 等の tenant 全体に影響する permission が付与されていないことを確認できる

### Requirement: SharePoint 対象範囲の限定
SPAutoPost が投稿できる SharePoint site / page library は、設定ファイルで明示的に指定されたものに限定しなければならない（SHALL）。任意 URL への投稿は禁止する（SHALL NOT）。

#### Scenario: 設定ファイルによる投稿先固定
- **WHEN** SPAutoPost が SharePoint 投稿処理を実行する
- **THEN** 投稿先 site は config の `sharepoint.site_id` から取得され、それ以外の site への投稿は拒否される

#### Scenario: 対象外 site への投稿拒否
- **WHEN** 設定ファイルに記載されていない SharePoint site への投稿が試みられる
- **THEN** エラーが発生し投稿処理は中断される。audit log に拒否された投稿先 URL が記録される
