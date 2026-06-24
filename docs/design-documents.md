# Design Documents

## Purpose

この文書は、SPAutoPost の設計書面の一覧と位置づけを整理します。

SPAutoPost は GitHub 駆動方式で進めるため、設計・実装・レビューはこのリポジトリ内の Spec / ADR / Runbook / Issue を正本として扱います。

## Product and Roadmap

| Document | Status | Purpose |
|---|---|---|
| `docs/product-brief.md` | Proposed | プロダクト目的、想定利用者、基本方針、成功条件 |
| `docs/roadmap.md` | Proposed | M0〜M6 の段階的ロードマップ |
| `docs/features.md` | Proposed | 機能分解と責務境界 |

## Core Specs

| Document | Status | Related Issues | Purpose |
|---|---|---|---|
| `docs/specs/initial-system.md` | Proposed | #1 | 初期システム境界、ワークフロー、主要データモデル |
| `docs/specs/m1-mvp-scope.md` | Accepted for M1 scope | #25, #26, #28, #31, #32, #33, #34, #35, #36 | M1 の完了条件、最小自動収集、記事生成、管理者確認、専用 SharePoint 投稿 |
| `docs/specs/architecture.md` | Accepted for MVP direction | #4, #6, #7, #9, #10, #21, #23, #26, #28, #29, #31 | Azure hosted core、Python jobs、TypeScript / Node.js Admin UI/API、PostgreSQL hosted PoC |
| `docs/specs/admin-ui-api.md` | Accepted for M1 boundary | #26, #31 | TypeScript / Node.js Admin UI/API の画面、API、Python core との境界 |
| `docs/specs/deployment.md` | Proposed | #24, #25, #28, #31 | Azure Container Apps / Jobs / PostgreSQL / Bicep / GitHub Actions skeleton |
| `docs/specs/admin-authentication.md` | Accepted for MVP direction | #26, #29 | Admin API / UI の Microsoft Entra ID ログイン認証 |
| `docs/specs/graph-authentication.md` | Accepted for local PoC and target hosted strategy | #2, #9, #24, #27, #32 | local PoC delegated、hosted runtime user-assigned managed identity 第一候補 |
| `docs/specs/sharepoint-publishing.md` | Accepted for MVP publishing mode | #2, #9, #20, #36 | SharePoint Site Page / News 投稿方式、専用 SharePoint への承認後投稿、冪等性 |
| `docs/specs/data-model.md` | Proposed | #3, #10, #20, #28 | Advisory / DraftPost / Publication / AuditEvent の正式モデル |
| `docs/specs/llm-provider.md` | Proposed | #6, #15, #16, #17, #18, #35 | LLM provider 分類、test_manual、Foundry / Azure OpenAI provider 方針 |
| `docs/specs/draft-composition.md` | Proposed | #8, #18, #19, #35 | 掲示板原稿の構成、文体、出典、AI 出力検査 |
| `docs/specs/source-collection.md` | Proposed | #7, #11, #12, #13, #21, #33, #34 | M1 sample source job、Firecrawl spike、M2 以降の本格 adapter |
| `docs/specs/normalization-and-triage.md` | Proposed | #14, #18, #19 | 名寄せ、重複排除、優先度判定、掲載候補判定 |
| `docs/specs/review-approval-workflow.md` | Proposed | #19, #20, #26, #29, #31, #36 | 人間レビュー、承認、差し戻し、公開制御 |
| `docs/specs/audit-log.md` | Proposed | #5, #10, #19, #22, #29, #36 | 監査ログ、correlation ID、保存禁止項目、user principal 記録 |
| `docs/specs/security-baseline.md` | Proposed | #5, #15, #22, #27, #29 | Secret、権限最小化、LLM 入力制限、投稿安全性 |
| `docs/specs/configuration.md` | Proposed | #4, #6, #9, #10, #28 | config、PostgreSQL、環境変数、feature flag、dry-run |
| `docs/specs/error-handling.md` | Proposed | #10, #20, #21, #22 | error code、retry/backoff、停止条件、部分失敗 |
| `docs/specs/external-collector-boundary.md` | Proposed | #13, #21 | crawler / collector 外部化時の import 境界 |

## Decision Records

| Document | Status | Purpose |
|---|---|---|
| `docs/decisions/2026-06-22-mvp-runtime-and-language.md` | Accepted | MVP は Python core + CLI/Batch command としつつ、運用コアは Azure hosted runtime に置く判断 |
| `docs/decisions/2026-06-22-azure-hosted-core.md` | Accepted | 定期収集・記事生成・投稿待ち管理・投稿処理を Azure Container Apps / Jobs 側に置く判断 |
| `docs/decisions/2026-06-22-storage-strategy.md` | Accepted | M1 hosted PoC は Azure PostgreSQL、SQLite は local/test 用にする判断 |
| `docs/decisions/2026-06-22-admin-ui-stack.md` | Accepted | Admin UI/API は TypeScript / Node.js とする判断 |
| `docs/decisions/2026-06-22-db-migration-strategy.md` | Accepted | DB schema の正本を SQL migration とする判断 |
| `docs/decisions/2026-06-22-admin-api-ui-in-m1.md` | Accepted | Admin API / UI の最小境界を M1 に含める判断 |
| `docs/decisions/2026-06-22-admin-authentication-entra-id.md` | Accepted | Admin API / UI のログイン認証に Microsoft Entra ID を使う判断 |
| `docs/decisions/2026-06-22-log-analytics-in-m6.md` | Accepted | Log Analytics 連携を M6 Production Hardening で扱う判断 |
| `docs/decisions/2026-06-22-sharepoint-list-vs-site-page.md` | Accepted | SharePoint Site Page / News article を MVP の投稿方式にする判断 |
| `docs/decisions/2026-06-22-llm-provider-strategy.md` | Proposed | 実稼働 provider と test provider の分離判断 |

## Runbooks

| Document | Status | Purpose |
|---|---|---|
| `docs/runbooks/operation.md` | Draft | 日常運用、dry-run、本番投稿前確認、失敗時対応 |
| `docs/runbooks/security-review.md` | Draft | 本番投入前のセキュリティレビュー checklist |
| `docs/runbooks/incident-response.md` | Draft | 誤投稿、重複投稿、Secret 露出、AI 誤出力時の初動対応 |

## Issue #23 M0 Review Matrix

この matrix は Issue #23 の対象文書を M0 review 用に整理します。各文書の `Status` は上表と各文書内の status を維持し、この表では Issue #23 としての review result を示します。

| Document | Current Status | Issue #23 Review Result | Deferred / Routed Issues | Notes |
|---|---|---|---|---|
| `docs/design-documents.md` | Document index / no document-level Status | M0 Accepted as review index | #23 | この matrix により Issue #23 対象文書の review result と follow-up routing を一元化する。 |
| `docs/specs/sharepoint-publishing.md` | Accepted for MVP publishing mode | M0 Accepted with routed open questions | #2, #9, #20, #36 | Site Page / News を MVP 投稿方式として採用済み。board contract、Graph 権限、publish / promote、添付・画像、公開範囲の未決事項は #2 に集約する。 |
| `docs/specs/data-model.md` | Proposed | M0 near-Accepted | #3, #20, #28 | Canonical model として利用可。#28 の storage baseline との差分は reconcile note 済みで、publication state / idempotency の詳細は #20 に残す。 |
| `docs/specs/llm-provider.md` | Proposed | M1+ deferred | #6, #15, #18, #35 | provider 分類と禁止事項は参照可。production / test provider 戦略、入力データ制限、provider 選定は #15 に集約し、この Issue では決定しない。 |
| `docs/specs/draft-composition.md` | Proposed | M1 near-Accepted for template, M3+ validation deferred | #8, #18, #19 | M1 template の方向性は #8 で実装済み。source-grounding validation と review workflow は #18 / #19 で確定する。 |
| `docs/specs/source-collection.md` | Proposed | M1 sample accepted, M2+ deferred | #7, #13, #21, #33, #34 | manual / sample source の方向性は M1 で利用可。本格 adapter、scheduler、external collector boundary は後続 Issue に残す。 |
| `docs/specs/normalization-and-triage.md` | Proposed | M2+ deferred | #14, #18, #19 | 名寄せ、重複排除、優先度判定は #14 で実装・確定する。M0 では設計候補として扱う。 |
| `docs/specs/review-approval-workflow.md` | Proposed | M4 deferred | #19, #20, #36 | 「人間レビュー前提」「approved 以外は publish 不可」は M0 方針として参照可。詳細な状態遷移と UI/API は #19 / #20 / #36 で確定する。 |
| `docs/specs/audit-log.md` | Proposed | M0 near-Accepted for minimum audit, M6 hardening deferred | #5, #10, #22 | minimal audit は #10 で実装済み。保持期間、保存先、本番 observability は #5 / #22 で確定する。 |
| `docs/specs/security-baseline.md` | Proposed | M0 near-Accepted | #5, #15, #22 | Secret 非コミット、最小権限、LLM 入力制限、投稿安全性は M0 方針として採用。production hardening と LLM data handling は #5 / #15 / #22 に残す。 |
| `docs/specs/configuration.md` | Proposed | M0 near-Accepted | #4, #6, #9, #28, #29 | config / env reference / dry-run / PostgreSQL 方針は実装参照可。SharePoint target と auth 詳細は #2 / #9 / #29 側で確定する。 |
| `docs/specs/error-handling.md` | Proposed | M1+ deferred with M0 safety constraints | #10, #20, #21, #22 | retry で重複投稿しない、Secret を error に出さない、unsafe publish を止める方針は M0 で採用。詳細な retry/backoff と production response は後続 Issue で確定する。 |
| `docs/specs/external-collector-boundary.md` | Proposed | M5 deferred | #13, #21, #22 | M0 では将来境界として参照のみ。API / queue import、外部 collector trust boundary は #21 以降で確定する。 |
| `docs/runbooks/operation.md` | Draft | M6 deferred runbook draft | #20, #22, #36 | dry-run、manual run、publish 前確認の checklist は参照可。本番運用手順は #22 と publish 実装後に更新する。 |
| `docs/runbooks/security-review.md` | Draft | M6 deferred runbook draft | #5, #15, #22 | review checklist の骨子は参照可。Graph 権限、LLM data handling、production hardening は #5 / #15 / #22 で確定する。 |
| `docs/runbooks/incident-response.md` | Draft | M6 deferred runbook draft | #20, #22, #36 | incident type と初動対応の骨子は参照可。実運用の連絡先、保存先、修正手順は #22 と publish 実装後に確定する。 |
| `docs/decisions/2026-06-22-sharepoint-list-vs-site-page.md` | Accepted | M0 Accepted with routed open questions | #2, #9, #20 | Site Page / News article 採用は Accepted。Open Follow-ups は #2 に集約し、この Issue では決定しない。 |
| `docs/decisions/2026-06-22-llm-provider-strategy.md` | Proposed | M3 deferred | #6, #15, #18, #35 | production / test separation の方向性は参照可。ADR acceptance は #15 の Spec 完了後に行う。 |

### Follow-up Routing

- SharePoint publishing / board contract の未決事項は #2 に集約する。実装系の #9 / #20 / #36 は、#2 と矛盾しない範囲で進める。
- LLM provider strategy の未決事項は #15 に集約する。#6 / #18 / #35 は、production provider 選定や subscription 自動化を決めない範囲で扱う。
- この review では speculative follow-up Issue を作成しない。既存 Issue に紐づけられない gap は、実装せず Issue / Spec 更新を要求する。

### Implementation-Before-Spec Gaps

- `docs/specs/data-model.md`: #28 で storage baseline が先行済み。`source_refs` と `event_type` の差分は本文の reconcile note に記録済みで、残る publication state / idempotency は #20 が扱う。
- `docs/specs/llm-provider.md`: #6 で provider interface / mock provider が先行済み。production / test provider 戦略は #15、optional provider spike は #35 が扱う。
- `docs/specs/draft-composition.md`: #8 で template 実装が先行済み。source-grounding validation は #18、review workflow は #19 が扱う。
- `docs/specs/source-collection.md`: #33 で sample source job が先行済み。本格 adapter / collector boundary は #13 / #21 / #34 が扱う。
- `docs/specs/audit-log.md` と `docs/specs/error-handling.md`: #10 で dry-run preview と minimal audit が先行済み。本番 observability、保持、incident-ready logging は #22 が扱う。

## Reading Order for Implementation Agents

1. `README.md`
2. `AGENTS.md`
3. `docs/project-rules.md`
4. 対象 Issue
5. 対象 Issue に関連する Spec
6. 必要に応じて ADR / Runbook
7. OpenSpec change

## Status Policy

- Proposed: 設計案。Issue / review により変更可能。
- Accepted: 採用済み。実装は原則これに従う。
- Accepted for MVP direction: MVP の方向性として採用済み。ただし一部詳細は別 Issue で確定する。
- Accepted for MVP publishing mode: MVP の投稿方式として採用済み。ただし認証や公開詳細は別 Issue で確定する。
- Accepted for M1 scope: M1 完了条件として採用済み。
- Accepted for M1 boundary: M1 の実装境界として採用済み。ただし詳細な本番認証・運用方針は別 Issue で確定する。
- Deprecated: 廃止予定。
- Superseded: 別文書に置き換え済み。

## Next Step

M0 では、少なくとも次の文書を Accepted に近づけます。

- `docs/specs/architecture.md`
- `docs/specs/m1-mvp-scope.md`
- `docs/specs/sharepoint-publishing.md`
- `docs/specs/data-model.md`
- `docs/specs/admin-authentication.md`
- `docs/specs/graph-authentication.md`
- `docs/specs/security-baseline.md`
- `docs/specs/audit-log.md`
- `docs/specs/configuration.md`

M1 では、sample source job、DraftPost 自動生成、PostgreSQL storage、TypeScript / Node.js Admin UI/API、Entra ID login、Azure Container Apps / Jobs deployment skeleton、専用 SharePoint への承認後投稿を含めます。
