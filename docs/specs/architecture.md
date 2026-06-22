# Architecture Specification

## Status

Accepted for MVP direction. Proposed for Microsoft Graph authentication and detailed Azure deployment parameters.

## Purpose

この Spec は、SPAutoPost の MVP アーキテクチャ、Azure 上の実行形態、実装言語、主要モジュール、データフロー、管理画面化方針、将来拡張方針を定義します。

## Architecture Decision Summary

MVP では、次の構成を採用します。

- Core Language: Python
- Local/Dev Interface: CLI / Batch command
- Hosted Runtime: Azure Container Apps / Azure Container Apps Jobs を主候補とする
- Scheduled Collection: ユーザー端末ではなく Azure 上の scheduled job / worker で実行する
- Admin Review: 管理者が生成記事を確認・修正・確定できる Admin API / UI を M1 に含める
- Frontend/API: 管理画面が必要になった段階で TypeScript / Node.js を採用する
- Storage: MVP は SQLite + YAML/JSON fixtures とする。量、同時実行、運用要件が増えたら Azure managed database へ移行する
- SharePoint Publishing: SharePoint Site Page / News article 形式を採用する
- Publishing Safety: draft / review / approval を基本とし、人間確認なしの本番自動公開は MVP 対象外
- LLM: mock provider を必須とし、production provider は provider interface 経由で追加する
- Observability: MVP では app-level audit log を実装し、Log Analytics 連携は M6 Production Hardening で扱う
- External Collector: MVP では import schema と境界のみを定義する

## Key Architecture Decision

SPAutoPost の定期収集、記事生成、投稿待ち管理、投稿処理は、人間ユーザーの端末に依存させません。

常時起動または定期起動できる Azure 上の container runtime を運用コアに据えます。

CLI / Batch は次の用途に残します。

- ローカル開発
- dry-run
- 手動再実行
- 障害時の補助操作
- Container Apps Jobs から呼び出される command entrypoint

## Target Runtime Model

```text
Azure Container Apps Environment
  ├─ SPAutoPost Admin/API App
  │    ├─ Review / Approval API
  │    ├─ Draft management
  │    ├─ Publication management
  │    └─ Audit query
  │
  ├─ SPAutoPost Scheduled Jobs
  │    ├─ collect-advisories
  │    ├─ normalize-and-triage
  │    ├─ generate-drafts
  │    └─ publish-approved
  │
  ├─ Storage
  │    ├─ SQLite for MVP
  │    ├─ Advisory / DraftPost / Publication / AuditEvent
  │    └─ fixtures / import files
  │
  └─ External Services
       ├─ NVD / MyJVN / KEV / vendor feeds
       ├─ LLM providers
       └─ Microsoft Graph / SharePoint Site Page / News
```

## MVP Runtime Model

MVP の最小実装単位は Python CLI / Batch command とします。

```text
spautopost <command> [options]
```

想定 command:

```text
validate-config
import-advisory
collect-advisories
normalize
triage
generate-draft
validate-draft
request-review
approve
publish-dry-run
publish-draft
audit-export
serve-admin-api
```

MVP 初期は CLI / Batch で縦串を通します。ただし、設計上は Azure Container Apps Jobs から各 command を起動できるようにします。

Admin API / UI は M1 に含めます。管理者が記事を確認、修正、確定し、その後 SharePoint Site Page / News に投稿する流れを前提にします。

## High-Level Architecture

```text
SPAutoPost Core Python Package
  ├─ Config Loader
  ├─ Source Input / Source Adapters
  ├─ Normalization Engine
  ├─ Triage Engine
  ├─ Draft Composition Engine
  ├─ LLM Provider Interface
  │   ├─ Mock Provider
  │   ├─ Microsoft Foundry / Azure OpenAI Provider future
  │   └─ Generic LLM API Provider future
  ├─ Draft Validation
  ├─ Review / Approval State
  ├─ SharePoint Site Page / News Publisher
  ├─ Storage Port
  └─ Audit Logger

Entrypoints
  ├─ Python CLI / Batch
  ├─ Azure Container Apps Jobs
  └─ Admin API / UI
```

## Data Flow

```text
Scheduled Job / Manual Import
  -> SourceRecord
  -> Advisory
  -> Triage Result
  -> DraftInput
  -> LLM Provider
  -> DraftPost
  -> Draft Validation
  -> Admin Review / Approval
  -> SharePoint Site Page / News Draft or Publish
  -> AuditEvent
```

## Module Responsibilities

### Config Loader

- config file を読み込む
- environment variable 参照を解決する
- Secret をログに出さない
- unsafe publish config を検出する
- Azure hosted runtime と local runtime の設定差分を扱う

### Source Input / Source Adapters

- 手動入力 YAML/JSON を読み込む
- NVD / MyJVN / KEV / vendor adapter を後続で追加可能にする
- 定期収集 job から実行できる
- 将来の external collector import に備える

### Normalization Engine

- SourceRecord を Advisory に変換する
- CVE / JVN / vendor advisory を名寄せする
- 重複排除用 key を生成する

### Triage Engine

- severity、KEV、exploit status、internal relevance から priority / urgency を算出する
- publication candidate を判定する
- reviewer override を許容する

### Draft Composition Engine

- Advisory から DraftInput を生成する
- prompt template / article template を適用する
- LLM Provider Interface 経由で DraftPost を生成する
- scheduled job と manual regeneration の両方から呼び出せる

### LLM Provider Interface

- MVP では mock provider を必須実装する
- production provider は interface 経由で追加する
- ChatGPT / Claude subscription は test_manual として手動検証枠に分離する

### Draft Validation

- required sections を確認する
- 出典不足、危険な詳細、過剰断定、根拠不明主張を warning/error とする

### Review / Approval State

- DraftPost の status を管理する
- 管理者が記事を確認、修正、確定できるようにする
- M1 で Admin API / UI の最小機能を含める
- approved でない DraftPost は publish できない

### SharePoint Site Page / News Publisher

- SharePoint Site Page / News article 形式で投稿 payload を作成する
- dry-run preview を提供する
- test site / draft posting を扱う
- approved item のみ publish 対象にする
- idempotency_key で重複投稿を防ぐ
- List item 投稿は MVP の主経路ではない

### Storage

MVP では SQLite を採用します。

保存対象:

- SourceRecord metadata
- Advisory
- DraftPost
- ReviewEvent
- Publication
- AuditEvent

fixture:

- manual advisory input
- mock provider response
- test publication payload

移行方針:

- データ量、同時実行、バックアップ、監査保持、複数インスタンス運用の要件が増えたら Azure managed database へ移行する
- 移行候補は Azure SQL Database、PostgreSQL-compatible managed DB、Azure Storage / Table Storage とする
- SQLite schema は将来移行しやすいように明示的に管理する

### Audit Logger

- すべての主要操作に correlation_id を付与する
- provider、prompt_version、reviewer、publication result を記録する
- Secret を保存しない
- MVP では app-level audit log を実装する
- Log Analytics 連携は M6 Production Hardening で扱う

## Trust Boundaries

```text
External Sources
  -> SPAutoPost controlled processing on Azure
  -> LLM Provider
  -> Admin Reviewer
  -> Microsoft Graph / SharePoint Site Page / News
```

注意する境界:

- 外部情報源からの入力は信頼しない
- LLM provider へ渡す情報は最小化する
- SharePoint 投稿先は config で固定する
- Secret は repository / log / fixture に保存しない
- ユーザー端末を定期収集・投稿処理の信頼境界に含めない

## MVP Non-Goals

- 複雑な多段承認
- 本番自動公開
- 本格 scheduler orchestration platform
- 本格 external crawler 実装
- SIEM / ITSM 連携
- Log Analytics 連携
- PostgreSQL / Azure SQL などの managed database 確定

## Future Architecture

管理 UI/API では、TypeScript / Node.js を候補とします。

候補:

```text
TypeScript / Node.js Admin UI
  -> Admin API
      -> SPAutoPost Core Python package or service boundary
          -> Storage / LLM Provider / SharePoint Publisher
```

または:

```text
External Collector
  -> Normalized Advisory Import
      -> SPAutoPost Azure Jobs / API
          -> Draft / Review / SharePoint Publish
```

## Open Questions

MVP 実装前または M1 途中で決める必要がある未決事項:

- Microsoft Graph 認証方式を delegated / application / managed identity のどれにするか
- Azure OpenAI / Foundry provider を M1 に含めるか、M3 まで待つか
- Container Apps の app / job 分割をどこまで M1 に含めるか
- SQLite を Azure hosted runtime 上でどのように永続化するか
- Admin API / UI を Python 側で最小実装するか、M1 から TypeScript / Node.js を入れるか

## Related Issues

- #2 Confirm SharePoint announcement board contract
- #3 Define canonical advisory, draft, and publication data model
- #4 Initialize application skeleton and configuration policy
- #6 Implement LLM provider interface with mock provider
- #7 Implement manual advisory input and validation
- #9 Implement SharePoint connector proof-of-concept
- #10 Implement dry-run preview and minimal audit log
- #21 Add scheduler and external collector import boundary
- #23 Review and finalize detailed design documents
- #26 Define minimal admin review API and UI boundary
