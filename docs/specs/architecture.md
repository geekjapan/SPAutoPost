# Architecture Specification

## Status

Accepted for MVP runtime decisions. Proposed for storage, authentication, and provider implementation details.

## Purpose

この Spec は、SPAutoPost の MVP アーキテクチャ、実行形態、実装言語、主要モジュール、データフロー、将来拡張方針を定義します。

## Architecture Decision Summary

MVP では、次の構成を採用します。

- Language: Python
- Runtime: CLI / Batch application
- Frontend: MVP 対象外。画面が必要になった段階で TypeScript / Node.js を採用する
- Serverization: 早めにサーバへ載せ、管理画面化できるようにする。ただし MVP の初期実装は CLI / Batch を優先する
- Storage: SQLite + YAML/JSON fixtures を第一候補とする。最終確定は #3 / #23 で扱う
- SharePoint Publishing: SharePoint Site Page / News article 形式を採用する
- Publishing Safety: dry-run / test posting / draft posting を基本とし、本番自動公開は MVP 対象外
- LLM: mock provider を必須とし、production provider は provider interface 経由で追加する
- Scheduler: MVP 対象外。手動実行または簡易 batch 実行を優先する
- External Collector: MVP では import schema と境界のみを定義する

## MVP Runtime Model

MVP は常駐サービスではなく、CLI / Batch として実行します。

```text
spautopost <command> [options]
```

想定 command:

```text
validate-config
import-advisory
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

MVP では Web UI、API server、常駐 worker、複雑な scheduler は対象外とします。ただし、後続でサーバ化しやすいよう、core logic は CLI に閉じ込めず、module / package として分離します。

## High-Level Architecture

```text
SPAutoPost CLI / Batch
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
  ├─ Storage
  │   ├─ SQLite proposed
  │   └─ YAML/JSON fixtures
  └─ Audit Logger
```

## Data Flow

```text
Manual Advisory YAML/JSON
  -> SourceRecord
  -> Advisory
  -> Triage Result
  -> DraftInput
  -> LLM Provider
  -> DraftPost
  -> Draft Validation
  -> Human Review / Approval
  -> SharePoint Site Page / News Draft or Test Posting
  -> AuditEvent
```

## Module Responsibilities

### Config Loader

- config file を読み込む
- environment variable 参照を解決する
- Secret をログに出さない
- unsafe publish config を検出する

### Source Input / Source Adapters

- 手動入力 YAML/JSON を読み込む
- NVD / MyJVN / KEV / vendor adapter を後続で追加可能にする
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

### LLM Provider Interface

- MVP では mock provider を必須実装する
- production provider は interface 経由で追加する
- ChatGPT / Claude subscription は test_manual として手動検証枠に分離する

### Draft Validation

- required sections を確認する
- 出典不足、危険な詳細、過剰断定、根拠不明主張を warning/error とする

### Review / Approval State

- DraftPost の status を管理する
- MVP では CLI と SQLite proposed による状態管理でよい
- approved でない DraftPost は publish できない

### SharePoint Site Page / News Publisher

- SharePoint Site Page / News article 形式で投稿 payload を作成する
- dry-run preview を提供する
- test site / draft posting を扱う
- idempotency_key で重複投稿を防ぐ
- List item 投稿は MVP の主経路ではない

### Storage

MVP では SQLite を第一候補とします。

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

### Audit Logger

- すべての主要操作に correlation_id を付与する
- provider、prompt_version、reviewer、publication result を記録する
- Secret を保存しない

## Trust Boundaries

```text
External Sources
  -> SPAutoPost controlled processing
  -> LLM Provider
  -> Human Reviewer
  -> Microsoft Graph / SharePoint Site Page / News
```

注意する境界:

- 外部情報源からの入力は信頼しない
- LLM provider へ渡す情報は最小化する
- SharePoint 投稿先は config で固定する
- Secret は repository / log / fixture に保存しない

## MVP Non-Goals

- Web UI
- API server
- 常駐 worker
- 本格 scheduler
- 本番自動公開
- 複雑な多段承認
- 本格 external crawler 実装
- SIEM / ITSM 連携
- PostgreSQL / Azure SQL などの本番 DB 選定

## Future Architecture

画面が必要になった段階で、TypeScript / Node.js による frontend または API layer を追加します。

将来候補:

```text
TypeScript / Node.js Web UI
  -> SPAutoPost API layer
      -> Python core package
          -> Storage / LLM Provider / SharePoint Publisher
```

または:

```text
External Collector
  -> Normalized Advisory Import
      -> SPAutoPost CLI / Worker / API
          -> Draft / Review / SharePoint Publish
```

## Open Questions

MVP 実装前または M1 途中で決める必要がある未決事項:

- MVP の SQLite schema をどこまで固定するか
- Microsoft Graph 認証方式を delegated / application / managed identity のどれにするか
- Azure OpenAI / Foundry provider を M1 に含めるか、M3 まで待つか
- review / approve 操作を CLI command とするか、ファイル編集 workflow とするか
- 管理画面化の開始 Milestone を M2/M3/M4 のどこに置くか

## Related Issues

- #2 Confirm SharePoint announcement board contract
- #3 Define canonical advisory, draft, and publication data model
- #4 Initialize application skeleton and configuration policy
- #6 Implement LLM provider interface with mock provider
- #7 Implement manual advisory input and validation
- #9 Implement SharePoint connector proof-of-concept
- #10 Implement dry-run preview and minimal audit log
- #23 Review and finalize detailed design documents
