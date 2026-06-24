## ADDED Requirements

### Requirement: Operational core runs on Azure container runtime

SPAutoPost の定期収集、記事生成、投稿待ち管理、投稿処理（運用コア）は、Azure 上の常時起動または定期起動できる container runtime（主候補: Azure Container Apps / Azure Container Apps Jobs）で実行しなければならない（SHALL）。運用コアを人間ユーザーの端末に依存させてはならない（SHALL NOT）。この方針は `docs/specs/architecture.md` と ADR `docs/decisions/2026-06-22-azure-hosted-core.md`（Accepted）を正本とする。

#### Scenario: 定期収集を端末非依存で実行する
- **WHEN** 定期収集 / 記事生成 / publish-approved を実行する必要がある
- **THEN** それらは Azure container runtime（Container Apps / Jobs）上の scheduled job / worker として実行され、特定ユーザー端末の起動・接続を前提としない

#### Scenario: ユーザー端末は運用コアではない
- **WHEN** ユーザー端末上で CLI を起動する
- **THEN** それは開発 / dry-run / 手動再実行 / 障害補助の用途であり、定期収集・投稿処理の運用コアまたは信頼境界には含めない

### Requirement: CLI / Batch is a job entrypoint, not the operational core

Python CLI / Batch command は、Azure Container Apps Jobs から呼び出される command entrypoint、ならびにローカル開発・dry-run・手動再実行・障害時補助として残さなければならない（SHALL）。CLI / Batch を定期収集・投稿処理の運用コアそのものとして位置づけてはならない（SHALL NOT）。

#### Scenario: Jobs から同一 command を呼び出す
- **WHEN** Azure Container Apps Jobs が collect-advisories / normalize-and-triage / generate-drafts / publish-approved を実行する
- **THEN** それらは Python core command entrypoint として呼び出され、ローカルで実行する CLI と同一の command 設計を共有する

### Requirement: M1 deployment skeleton scope is defined

M1 で実装すべき deployment skeleton の範囲を明確にしなければならない（SHALL）。範囲は Azure Container Apps Admin UI/API、Azure Container Apps Jobs、Azure Database for PostgreSQL Flexible Server、environment variables、container image build、GitHub Actions skeleton、Bicep skeleton を含む。本番運用 IaC の完成、本格 monitoring、Log Analytics 連携、Blue/green、DR / HA を M1 deployment skeleton の完了条件に含めてはならない（SHALL NOT）。詳細は `docs/specs/deployment.md` を正本とし、実装は Issue #25 で行う。

#### Scenario: M1 skeleton の構成要素を参照する
- **WHEN** M1 で deployment skeleton（Issue #25）を実装する
- **THEN** 対象は Admin UI/API App・Scheduled Jobs・PostgreSQL・env vars・container build・GitHub Actions skeleton・Bicep skeleton に限定され、本番 deploy automation や Log Analytics 連携は含めない

### Requirement: Storage, identity, and logging unresolved items are issue-tracked

storage / identity / logging の未決事項は、それぞれ追跡用の GitHub Issue に結び付けられていなければならない（SHALL）。最低限、storage は #28、identity（Graph 認証方式・Entra ID ログイン・ローカル delegated PoC）は #27 / #29 / #32、logging（Log Analytics 連携）は #30 に紐づけ、`docs/specs/architecture.md` から参照可能でなければならない（SHALL）。これらの未決事項の本番確定は MVP / M1 の対象外とする。

#### Scenario: 未決事項から追跡 Issue へ辿れる
- **WHEN** storage / identity / logging の未決事項を確認する
- **THEN** architecture.md から storage=#28、identity=#27 / #29 / #32、logging=#30 の追跡 Issue を参照でき、本番確定が後続 Issue に委ねられていることが分かる
