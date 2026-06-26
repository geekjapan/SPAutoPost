# Architecture Specification

## Status

Accepted for MVP direction. Proposed for Microsoft Graph hosted authentication and detailed Azure deployment parameters.

## Purpose

この Spec は、SPAutoPost の MVP アーキテクチャ、Azure 上の実行形態、実装言語、主要モジュール、データフロー、管理画面化方針、将来拡張方針を定義します。

## Architecture Decision Summary

MVP では、次の構成を採用します。

- Core Language: Python
- Local/Dev Interface: CLI / Batch command
- Hosted Runtime: Azure Container Apps / Azure Container Apps Jobs を主候補とする
- Scheduled Collection: ユーザー端末ではなく Azure 上の scheduled job / worker で実行する
- Admin UI/API: M1 から TypeScript / Node.js を採用する
- Storage: M1 hosted PoC は Azure Database for PostgreSQL Flexible Server を採用する
- Local/Test Storage: SQLite は local development、unit test、offline dry-run 用として残す
- SharePoint Publishing: SharePoint Site Page / News article 形式を採用する
- Publishing Safety: draft / review / approval を基本とし、人間確認なしの本番自動公開は MVP 対象外
- LLM: mock provider を必須とし、production provider は provider interface 経由で追加する
- Admin Login: Microsoft Entra ID を利用する
- Graph Local PoC: 当面は delegated permission を許容する
- Graph Hosted Runtime: user-assigned managed identity を採用する（第一候補）。fallback は application permission / app-only access（#27 確定済み）
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
  ├─ SPAutoPost Admin UI/API
  │    ├─ TypeScript / Node.js
  │    ├─ Microsoft Entra ID login
  │    ├─ Review / Approval API
  │    ├─ Draft management
  │    ├─ Publication management
  │    └─ Audit query
  │
  ├─ SPAutoPost Scheduled Jobs
  │    ├─ Python core commands
  │    ├─ collect-advisories
  │    ├─ normalize-and-triage
  │    ├─ generate-drafts
  │    └─ publish-approved
  │
  ├─ Storage
  │    ├─ Azure Database for PostgreSQL Flexible Server
  │    ├─ Advisory / DraftPost / Publication / AuditEvent
  │    └─ fixtures / import files
  │
  └─ External Services
       ├─ NVD / MyJVN / KEV / vendor feeds
       ├─ LLM providers
       └─ Microsoft Graph / SharePoint Site Page / News
```

## MVP Runtime Model

MVP の core processing は Python CLI / Batch command として実装します。

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
```

Admin UI/API は M1 に含め、TypeScript / Node.js で実装します。

## High-Level Architecture

```text
TypeScript / Node.js Admin UI/API
  ├─ Entra ID login
  ├─ DraftPost list/detail
  ├─ edit / approve / reject / request regeneration
  ├─ publish request
  └─ AuditEvent view

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

Storage
  ├─ PostgreSQL for M1 hosted PoC
  └─ SQLite for local/test only
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
  -> Admin UI Review / Approval
  -> SharePoint Site Page / News Draft or Publish
  -> AuditEvent
```

## Module Responsibilities

### TypeScript / Node.js Admin UI/API

- Microsoft Entra ID login を扱う
- DraftPost 一覧と詳細を表示する
- validation warning を表示する
- 管理者による記事修正要求を `AdminCommand` として enqueue する
- approve / reject / request regeneration を `AdminCommand` として enqueue する
- publish request を `AdminCommand` として enqueue する
- AuditEvent を参照する
- DraftPost の状態機械、ReviewEvent / AuditEvent 記録、publish 処理は直接実行しない

Python core 側では、DraftPost の状態機械、ReviewEvent / AuditEvent 記録、
publish 処理を所有する。

### Python CLI / Batch

- local development と dry-run を支える
- Azure Container Apps Jobs の command entrypoint として動作する
- 収集、正規化、トリアージ、記事生成、検証、投稿処理を呼び出す

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
- M1 で Admin UI/API の最小機能を含める
- approved でない DraftPost は publish できない

### SharePoint Site Page / News Publisher

- SharePoint Site Page / News article 形式で投稿 payload を作成する
- local PoC では delegated permission を許容する
- dry-run preview を提供する
- test site / draft posting を扱う
- approved item のみ publish 対象にする
- idempotency_key で重複投稿を防ぐ
- List item 投稿は MVP の主経路ではない

### Storage

M1 hosted PoC では Azure Database for PostgreSQL Flexible Server を採用します。

保存対象:

- SourceRecord metadata
- Advisory
- DraftPost
- ReviewEvent
- Publication
- AuditEvent
- AdminCommand

local/test:

- SQLite adapter を許容する
- manual advisory input、mock provider response、test publication payload は YAML/JSON fixture で扱う

### Audit Logger

- すべての主要操作に correlation_id を付与する
- provider、prompt_version、reviewer、publication result を記録する
- approve した user principal と publish を実行した identity を記録する
- Secret を保存しない
- MVP では app-level audit log を実装する
- Log Analytics 連携は M6 Production Hardening で扱う

## Trust Boundaries

```text
External Sources
  -> SPAutoPost controlled processing on Azure
  -> LLM Provider
  -> Admin Reviewer via Entra ID
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
- managed identity / app-only Graph 認証の M1 権限付与検証（method は #27 で確定、M1 で `Sites.Selected` 付与可否を検証）

## Open Questions

MVP 実装前または M1 途中で決める必要がある未決事項:

- Azure OpenAI / Foundry provider を M1 に含めるか、M3 まで待つか
- Container Apps の app / job 分割をどこまで M1 に含めるか

解消済み:

- Admin UI/API と Python core の呼び出し境界は #26 / ADR
- Azure hosted runtime の Graph 認証方式: user-assigned managed identity（第一候補）、app-only access（fallback）— #27 で確定
  `docs/decisions/2026-06-22-admin-core-boundary.md` で解消済み。M1 では
  read は PostgreSQL 直読み、write は `AdminCommand` 経由の非同期 handoff とする。

## Unresolved Items Tracking

storage / identity / logging の未決事項は、本番確定を MVP / M1 の対象外としつつ、
次の追跡 Issue に紐づける（Issue #24 受け入れ条件）。

- Storage: #28 PostgreSQL storage baseline（本番 DB 完全確定は後続）
- Identity: #29 Admin API/UI 向け Entra ID login /
  #32 local Graph delegated posting PoC（Graph 認証方式は #27 で確定済み）
- Logging: #30 Azure Log Analytics 連携（MVP は app-level audit log のみ、連携は M6）

## Acceptance Note (Issue #24)

Issue #24 の受け入れ条件は本 Spec と ADR `docs/decisions/2026-06-22-azure-hosted-core.md`
（Accepted）、`docs/specs/deployment.md` の M1 deployment skeleton 範囲、および上記
Unresolved Items Tracking で満たす。binding な不変条件は OpenSpec capability
`azure-hosted-core`（change: `issue-24-finalize-azure-hosted-core-architecture`）に固定する。

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
- #25 Add Azure Container Apps deployment skeleton
- #26 Define minimal admin review API and UI boundary
- #27 Decide Microsoft Graph authentication model
- #28 Implement PostgreSQL storage and migration baseline
- #29 Implement Entra ID login for Admin API/UI
- #30 Add Azure Log Analytics integration
- #32 Implement local Graph delegated posting PoC
