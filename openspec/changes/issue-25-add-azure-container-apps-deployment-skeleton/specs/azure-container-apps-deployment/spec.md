## ADDED Requirements

### Requirement: Container images define current runtime surfaces

SPAutoPost は、現在の repo shape に合わせて Python core と TypeScript Admin API の container image build premise を定義しなければならない（SHALL）。image build skeleton は本番 Azure resource 作成や Secret 登録を行ってはならない（SHALL NOT）。

#### Scenario: Core image build premise exists

- **WHEN** M1 deployment skeleton を確認する
- **THEN** Python core CLI を実行するための `Dockerfile.core` が存在し、`spautopost` command を container entrypoint から呼べる

#### Scenario: Admin image build premise exists

- **WHEN** M1 deployment skeleton を確認する
- **THEN** TypeScript Admin API skeleton を build / run するための `Dockerfile.admin` が存在する

### Requirement: Container Apps Jobs use a safe CLI entrypoint wrapper

Azure Container Apps Jobs は、job 名または引数から SPAutoPost CLI command を呼び分ける entrypoint wrapper skeleton を使わなければならない（SHALL）。wrapper は未知の job 名を成功扱いにしてはならない（SHALL NOT）。

#### Scenario: Known job command is dispatched

- **WHEN** wrapper に `collect` などの既知 job 名を渡す
- **THEN** wrapper は対応する `spautopost` CLI command を実行する

#### Scenario: Unknown job command fails closed

- **WHEN** wrapper に未定義 job 名を渡す
- **THEN** wrapper は非 0 終了し、実 publish や外部 API 呼び出しを行わない

### Requirement: Scheduled job command skeletons are safe by default

SPAutoPost は、dry-run、collect、generate、publish-approved の scheduled job command skeleton を提供しなければならない（SHALL）。まだ実装されていない外部 API / SharePoint publish path は no-op または stub とし、実 publish を行ってはならない（SHALL NOT）。

#### Scenario: Dry-run job performs validation only

- **WHEN** dry-run job を実行する
- **THEN** config validation と安全な preview だけを行い、外部投稿を行わない

#### Scenario: Publish-approved job is gated

- **WHEN** publish-approved job skeleton を実行する
- **THEN** approved item の publish pipeline が未実装であることを示し、SharePoint への作成・更新・公開は行わない

### Requirement: Local and hosted configuration are explicitly separated

SPAutoPost は、local run と Azure-intended hosted run の設定差分を documentation と example config で明示しなければならない（SHALL）。Secret は実値ではなく環境変数参照または Azure secret reference 例として扱わなければならない（SHALL）。

#### Scenario: Local config uses local-safe defaults

- **WHEN** local run の設定例を確認する
- **THEN** SQLite と dry-run を前提とし、production Secret 実値を含まない

#### Scenario: Hosted config uses secret references

- **WHEN** Azure-intended run の設定例を確認する
- **THEN** PostgreSQL と hosted env vars / secret references を前提とし、Secret 実値を含まない

### Requirement: Deployment documentation explains scope boundaries

README または docs は、local run と Azure-intended run の違い、Docker build、Container Apps Jobs command 例、M1 deployment skeleton の非対象範囲を説明しなければならない（SHALL）。

#### Scenario: Operator reads deployment skeleton docs

- **WHEN** operator が README または deployment docs を読む
- **THEN** local execution と Azure-intended execution の違い、Secret reference 方針、Azure resource creation が含まれないことを理解できる
