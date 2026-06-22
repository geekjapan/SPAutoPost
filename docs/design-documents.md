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
| `docs/specs/initial-system.md` | Proposed | #1 | 初期システム境界、ワークフロー、データモデル概要 |
| `docs/specs/architecture.md` | Proposed | #4, #6, #7, #9, #10, #23 | MVP アーキテクチャ、Python CLI/Batch、主要モジュール、将来拡張 |
| `docs/specs/sharepoint-publishing.md` | Proposed | #2, #9, #20 | SharePoint 投稿方式、権限、下書き、公開、冪等性 |
| `docs/specs/data-model.md` | Proposed | #3, #10, #20 | Advisory / DraftPost / Publication / AuditEvent の正式モデル |
| `docs/specs/llm-provider.md` | Proposed | #6, #15, #16, #17, #18 | LLM provider 分類、実稼働/テスト分離、入力制限、監査 |
| `docs/specs/draft-composition.md` | Proposed | #8, #18, #19 | 掲示板原稿の構成、文体、出典、AI 出力検査 |
| `docs/specs/source-collection.md` | Proposed | #7, #11, #12, #13, #21 | NVD / MyJVN / KEV / vendor / manual / external import の収集仕様 |
| `docs/specs/normalization-and-triage.md` | Proposed | #14, #18, #19 | 名寄せ、重複排除、優先度判定、掲載候補判定 |
| `docs/specs/review-approval-workflow.md` | Proposed | #19, #20 | 人間レビュー、承認、差し戻し、再生成、公開制御 |
| `docs/specs/audit-log.md` | Proposed | #5, #10, #19, #22 | 監査ログ、correlation ID、保存禁止項目 |
| `docs/specs/security-baseline.md` | Proposed | #5, #15, #22 | Secret、権限最小化、LLM 入力制限、投稿安全性 |
| `docs/specs/configuration.md` | Proposed | #4, #6, #9, #10 | config、環境変数、feature flag、dry-run |
| `docs/specs/error-handling.md` | Proposed | #10, #20, #21, #22 | error code、retry/backoff、停止条件、部分失敗 |
| `docs/specs/external-collector-boundary.md` | Proposed | #13, #21 | crawler / collector 外部化時の import 境界 |

## Decision Records

| Document | Status | Purpose |
|---|---|---|
| `docs/decisions/2026-06-22-mvp-runtime-and-language.md` | Accepted | MVP は Python + CLI/Batch とし、画面が必要になったら TypeScript / Node.js を検討する判断 |
| `docs/decisions/2026-06-22-sharepoint-list-vs-site-page.md` | Proposed | SharePoint List item と Site Page の選定判断を記録するための ADR |
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
- Deprecated: 廃止予定。
- Superseded: 別文書に置き換え済み。

## Next Step

M0 では、少なくとも次の文書を Accepted に近づけます。

- `docs/specs/architecture.md`
- `docs/specs/sharepoint-publishing.md`
- `docs/specs/data-model.md`
- `docs/specs/security-baseline.md`
- `docs/specs/audit-log.md`
- `docs/specs/configuration.md`
