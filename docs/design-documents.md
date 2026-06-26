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
| `docs/specs/graph-authentication.md` | Decided（#27 確定済み） | #2, #9, #24, #32 | local PoC delegated（Device Code Flow）、hosted runtime user-assigned managed identity 確定、Graph permission 最小化・対象 site 固定方針 |
| `docs/specs/sharepoint-publishing.md` | Accepted for MVP publishing mode | #2, #9, #20, #36 | SharePoint Site Page / News 投稿方式、専用 SharePoint への承認後投稿、冪等性 |
| `docs/specs/data-model.md` | Accepted for M0 | #3, #10, #20, #28 | Advisory / DraftPost / Publication / AuditEvent の正式モデル |
| `docs/specs/llm-provider.md` | Proposed | #6, #15, #16, #17, #18, #35 | LLM provider 分類、test_manual、Foundry / Azure OpenAI provider 方針 |
| `docs/specs/draft-composition.md` | Proposed | #8, #18, #19, #35 | 掲示板原稿の構成、文体、出典、AI 出力検査 |
| `docs/specs/source-collection.md` | Proposed | #7, #11, #12, #13, #21, #33, #34 | M1 sample source job、Firecrawl spike、M2 以降の本格 adapter |
| `docs/specs/normalization-and-triage.md` | Proposed | #14, #18, #19 | 名寄せ、重複排除、優先度判定、掲載候補判定 |
| `docs/specs/review-approval-workflow.md` | Proposed | #19, #20, #8, #18 | 人間レビュー、承認、差し戻し、公開制御 |
| `docs/specs/audit-log.md` | Proposed | #5, #10, #19, #22, #29, #36 | 監査ログ、correlation ID、保存禁止項目、user principal 記録 |
| `docs/specs/security-baseline.md` | Proposed | #5, #15, #22, #27, #29 | Secret、権限最小化、LLM 入力制限、投稿安全性 |
| `docs/specs/configuration.md` | Accepted for M0 | #4, #6, #9, #10, #28 | config、PostgreSQL、環境変数、feature flag、dry-run |
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
- Accepted for M0: M0（Project Foundation）の基礎設計として確定済み。人間ゲート判断を要さない。`Accepted for MVP direction` / `Accepted for MVP publishing mode` も M0 で採用済みの variant であり、Review & Status Matrix では同じ **Accepted for M0** disposition bucket に属する。
- Deprecated: 廃止予定。
- Superseded: 別文書に置き換え済み。

## Review & Status Matrix (Issue #23)

この節は Issue #23（M0 詳細設計文書レビュー）の **中央レビュー記録（正本）** です。対象 18 文書の M0 における位置づけ、確定 Milestone、追跡 Issue、未決事項の集約先を一覧します。フィールド表・spec 本文はここに複製せず、各文書を正本として参照します。

### Disposition の定義

- **Accepted for M0**: foundational に確定済み。人間ゲート判断を要さない。実装は原則これに従う。
- **M0 — finalization tracked**: M0 で扱うが、認証 / Secret / 投稿 / compliance に関わる最終確定を担う Issue が未決のため、本レビューでは Accepted に flip しない（human-gated）。
- **Proposed → M1+**: 設計は安定だが、確定は記載の後続 Milestone / Issue で行う。
- **Draft runbook → M6**: 運用 playbook。本番投入前（#22 Production Hardening, M6）に finalize。

「M0 Disposition」列はレビュー分類 bucket であり、各文書の Core Specs 表の Status（lifecycle ラベル）はその bucket に属する。例: `sharepoint-publishing.md` の Status `Accepted for MVP publishing mode` は **Accepted for M0** bucket に属する（Status Policy 参照）。両者は矛盾しない。

### Matrix

| Document | M0 Disposition | 確定 Milestone | 追跡 / route Issue | 未決事項の集約先 |
|---|---|---|---|---|
| `docs/design-documents.md` | Accepted for M0（本レビュー記録） | M0 | #23 | — |
| `docs/specs/sharepoint-publishing.md` | Accepted for M0（MVP publishing mode） | M0 / M1 | #2, #9, #20, #36 | **#2**（権限・公開範囲・添付・News promote）。List item vs Site Page/News の MVP 方針は Accepted 済み。 |
| `docs/specs/data-model.md` | Accepted for M0 | M0 | #3, #10, #20, #28 | #28（multi-source）, #10（event_type 権威付け） |
| `docs/specs/configuration.md` | Accepted for M0 | M0 | #4, #6, #9, #10, #28 | — |
| `docs/decisions/2026-06-22-sharepoint-list-vs-site-page.md` | Accepted for M0 | M0 | #2, #9, #20 | **#2**（Open Follow-ups: News promote・permission 種別・添付） |
| `docs/specs/security-baseline.md` | M0 — finalization tracked | M0 | #5 | #5（baseline 確定）, **#15**（LLM 入力制限）, #22 |
| `docs/specs/audit-log.md` | M0 — finalization tracked | M0 | #5, #10, #19, #22 | #5（baseline）, #22（retention 本番確定） |
| `docs/specs/graph-authentication.md` | Accepted for M0（#27 確定済み） | M0 | #2, #9, #24, #32 | **#2**（Graph permission 付与確認・News promote 等は M1 以降） |
| `docs/specs/llm-provider.md` | Proposed → M1+ | M3 | #6, #15, #16, #17, #18 | **#15**（provider 戦略・本番/テスト分離） |
| `docs/decisions/2026-06-22-llm-provider-strategy.md` | Proposed → M1+ | M3 | #6, #15, #16, #17, #18 | **#15** |
| `docs/specs/draft-composition.md` | Proposed → M1+ | M3 | #8, #18, #19 | #18（AI 出力検査）, #19 |
| `docs/specs/source-collection.md` | Proposed → M1+ | M2 | #7, #11, #12, #13, #21 | #11–#13（adapter）, #21（外部 collector） |
| `docs/specs/normalization-and-triage.md` | Proposed → M1+ | M2 | #14, #18, #19 | #14, #18 |
| `docs/specs/review-approval-workflow.md` | Proposed → M1+ | M4 | #19, #20, #8, #18 | #19 |
| `docs/specs/error-handling.md` | Proposed → M1+ | M4 / M6 | #10, #20, #21, #22 | #20（idempotency）, #22（本番 retry/backoff） |
| `docs/specs/external-collector-boundary.md` | Proposed → M1+ | M5 | #13, #21, #22 | #21 |
| `docs/runbooks/operation.md` | Draft runbook → M6 | M6 | #22 | #22（correction 手順・Publication state） |
| `docs/runbooks/security-review.md` | Draft runbook → M6 | M6 | #5, #22 | #22 |
| `docs/runbooks/incident-response.md` | Draft runbook → M6 | M6 | #22 | #22 |

### 未決事項の集約（routing）

- **SharePoint お知らせ掲示板 contract** の未決事項（必要 Graph 権限、delegated / application / managed identity、公開範囲、添付・画像、News publish/promote、投稿失敗時挙動）は **Issue #2** に集約する。MVP の投稿方式は Site Page / News として Accepted 済みであり、この review では List item vs Site Page/News の選択を再オープンしない。参照元: `sharepoint-publishing.md`「Open Questions」、sharepoint ADR「Open Follow-ups」、`graph-authentication.md`。本レビューは #2 の残 contract 判断自体は行わない（route のみ）。
- **LLM provider 戦略** の未決事項（production_api / production_flow / generic_api / test_manual の分離、provider 契約・費用、prompt/output 保存方針、provider 切替方針）は **Issue #15** に集約する。参照元: `llm-provider.md`、`security-baseline.md`、llm-provider-strategy ADR。本レビューは #15 の戦略判断自体は行わない（route のみ）。

### 実装前 Spec 不足の追跡（Issue 化）

実装前に確定が必要な spec 不足は、すべて既存 Issue で追跡済み。**本レビューでは新規の投機的 Issue を作成しない。**

- M0 で未確定の spec gap: **#2**（SharePoint contract）、**#5**（security / secrets / audit / compliance baseline）。いずれも M0 Milestone・OPEN。#27（Microsoft Graph authentication model）は本 PR で確定済み。
- 後続 spec の確定は各 Change/Spike Issue で追跡: #9（SharePoint PoC）、#11–#14（collection / triage）、#16–#22（LLM / review / idempotency / scheduler / hardening）、#32–#36（local Graph PoC / login / spike / publish）。

## Next Step

- M0 の残り spec 確定（#2 / #5）が完了した時点で、`security-baseline.md` / `audit-log.md` を「M0 — finalization tracked」から Accepted へ昇格する。（#27 は確定済み）
- M1 では、sample source job、DraftPost 自動生成、PostgreSQL storage、TypeScript / Node.js Admin UI/API、Entra ID login、Azure Container Apps / Jobs deployment skeleton、専用 SharePoint への承認後投稿を含める。
