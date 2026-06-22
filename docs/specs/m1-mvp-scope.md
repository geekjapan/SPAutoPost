# M1 MVP Scope Specification

## Status

Accepted for M1 scope.

## Purpose

この Spec は、SPAutoPost の M1 MVP で到達すべき実用最小範囲を定義します。

## M1 Goal

M1 では、単なる手動入力デモではなく、最低限の自動収集、記事生成、管理者確認、確定、SharePoint Site Page / News 投稿までの縦串を通します。

正確性、情報源の網羅性、生成品質、本番 provider の完成度は後続 Milestone で高めます。

## Completion Criteria

M1 MVP は、次を満たすことで完了とします。

1. 何らかの自動収集または検索により、投稿候補情報を取得できる。
2. 取得した情報から DraftPost を自動生成できる。
3. 生成された DraftPost が PostgreSQL に保存される。
4. TypeScript / Node.js Admin UI/API で DraftPost を確認できる。
5. 管理者が記事を修正できる。
6. 管理者が確定または承認できる。
7. 確定後、専用 SharePoint Site Page / News に投稿できる。
8. Publication と AuditEvent が記録される。
9. Azure Container Apps / Jobs に載せるための skeleton がある。

## Implementation Order

M1 は次の順序で実装します。

1. PostgreSQL schema / migration baseline
2. Python core source and draft pipeline
3. TypeScript / Node.js Admin UI/API
4. Graph / SharePoint posting PoC
5. Azure Container Apps / Jobs deployment skeleton

Optional spike は M1 の本線を止めない範囲で並行実施します。

- Firecrawl source adapter spike
- optional LLM draft provider evaluation
- Foundry / Azure OpenAI provider spike
- generic LLM API provider spike

## Phase 1: PostgreSQL schema / migration baseline

目的:

- Advisory、DraftPost、ReviewEvent、Publication、AuditEvent の保存基盤を作る。
- Python core と TypeScript / Node.js Admin UI/API が共有する schema の正本を作る。

主な関連 Issue:

- #3 Define canonical advisory, draft, and publication data model
- #28 Implement PostgreSQL storage baseline

## Phase 2: Python core source and draft pipeline

目的:

- source input または sample source job から Advisory を作る。
- DraftPost を自動生成する。
- DraftPost / AuditEvent を PostgreSQL に保存する。

主な関連 Issue:

- #7 Implement manual advisory input and validation
- #8 Implement draft composition template for SharePoint announcements
- #33 Implement sample source job
- #35 Evaluate optional LLM draft providers

## Phase 3: TypeScript / Node.js Admin UI/API

目的:

- 生成された DraftPost を管理者が確認できるようにする。
- 管理者が修正、承認、差し戻し、投稿要求できるようにする。
- Entra ID login と最小 role を組み込む。

主な関連 Issue:

- #26 Define TypeScript Node.js Admin UI/API boundary
- #29 Implement Entra ID login for Admin API/UI
- #31 Implement TypeScript Node.js Admin UI API skeleton

## Phase 4: Graph / SharePoint posting PoC

目的:

- 管理者が確定した DraftPost を、専用 SharePoint Site Page / News に投稿する。
- local PoC では delegated permission を許容する。
- Publication と AuditEvent を記録する。

主な関連 Issue:

- #9 Implement SharePoint connector proof-of-concept
- #20 Implement SharePoint publish idempotency and state tracking
- #32 Implement local Graph delegated posting PoC
- #36 Implement approved publish to dedicated SharePoint News

## Phase 5: Azure Container Apps / Jobs deployment skeleton

目的:

- Python core jobs、TypeScript / Node.js Admin UI/API、PostgreSQL を Azure hosted PoC に載せるための skeleton を用意する。
- 本格運用ではなく、M1 の再現可能な deployment baseline を作る。

主な関連 Issue:

- #24 Finalize Azure hosted core architecture
- #25 Add Azure Container Apps deployment skeleton

## Source Collection Scope

M1 では、正確性よりも縦串の検証を優先します。

必須:

- manual / fixture input
- minimal automatic collection or search
- collected source metadata

候補:

- simple web/RSS search adapter
- NVD minimal query
- vendor advisory URL import
- Firecrawl adapter spike

M2 では NVD / MyJVN / KEV / vendor/RSS adapter を整理し、正規化と優先度付けを強化します。

## Draft Generation Scope

M1 では、記事が自動生成され、管理者が確認できることを重視します。

必須:

- deterministic template or mock provider
- DraftPost generation from collected input
- draft validation warning
- prompt/template version recording

任意:

- ChatGPT subscription を使った test_manual draft evaluation
- Azure OpenAI / Foundry provider spike
- generic LLM API provider spike

本番稼働に向けては、Foundry / Azure OpenAI provider へ移行する方針です。

## Publishing Scope

M1 では専用 SharePoint Site Page / News への投稿を許可します。

条件:

- 管理者が確定または承認していること
- 投稿先が専用 SharePoint site であること
- 投稿結果が Publication と AuditEvent に記録されること
- 人間確認なしの自動公開はしないこと

## Admin UI/API Scope

M1 では TypeScript / Node.js Admin UI/API を含めます。

必須:

- DraftPost list
- DraftPost detail
- edit draft
- approve / reject / request regeneration
- publish request
- AuditEvent view minimal
- Entra ID login

## Storage Scope

M1 hosted PoC は Azure Database for PostgreSQL Flexible Server を使います。

SQLite は local development、unit test、offline dry-run 用に残します。

## Non-Goals

M1 では次を対象外とします。

- 情報収集の完全性
- 生成記事の高精度化
- 本格的な多段承認
- 本格 crawler
- 本格 Log Analytics 連携
- 本番向け Foundry provider 完成
- hosted runtime の Graph 認証方式の最終本番確定

## Related Issues

- #7 Implement manual advisory input and validation
- #8 Implement draft composition template for SharePoint announcements
- #9 Implement SharePoint connector proof-of-concept
- #25 Add Azure Container Apps deployment skeleton
- #26 Define TypeScript Node.js Admin UI/API boundary
- #28 Implement PostgreSQL storage baseline
- #29 Implement Entra ID login for Admin API/UI
- #31 Implement TypeScript Node.js Admin UI API skeleton
- #32 Implement local Graph delegated posting PoC
- #33 Implement sample source job
- #34 Evaluate Firecrawl source adapter
- #35 Evaluate optional LLM draft providers
- #36 Implement approved publish to dedicated SharePoint News
