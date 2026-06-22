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
