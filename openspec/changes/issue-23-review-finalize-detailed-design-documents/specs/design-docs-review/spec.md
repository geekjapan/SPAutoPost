## ADDED Requirements

### Requirement: M0 Accepted document set is identified

詳細設計文書レビュー（Issue #23）は、M0 で Accepted とする文書集合を中央レビューマトリクスで特定しなければならない（SHALL）。M0 Accepted 集合には、人間ゲート判断を要さず foundational に確定済みの文書のみを含める。最低限 `docs/specs/sharepoint-publishing.md`（MVP publishing mode）、`docs/specs/data-model.md`、`docs/specs/configuration.md`、`docs/decisions/2026-06-22-sharepoint-list-vs-site-page.md` を M0 Accepted として特定し、`docs/design-documents.md` の Status を整合させなければならない（SHALL）。認証・Secret・投稿・LLM 契約に依存する文書を、その判断を担う Issue が未決のまま M0 Accepted に flip してはならない（SHALL NOT）。

#### Scenario: M0 Accepted 文書を中央マトリクスから特定する
- **WHEN** どの設計文書が M0 で Accepted かを確認する
- **THEN** `docs/design-documents.md` の Review & Status Matrix から M0 Accepted 集合を一覧でき、各文書の Status 表記がそれと整合している

### Requirement: M1+ deferred document set is identified

レビューは、後続 Milestone（M1 以降）で確定する Proposed / Draft / Deferred 文書集合を特定しなければならない（SHALL）。各 M1+ 文書には、確定を担う Milestone と既存追跡 Issue を中央マトリクスで対応付けなければならない（SHALL）。

#### Scenario: M1+ で確定する文書を追跡 Issue 付きで特定する
- **WHEN** M1 以降で確定する設計文書を確認する
- **THEN** 中央マトリクスから `llm-provider.md`（#15/M3）、`draft-composition.md`（#8/M3）、`source-collection.md`（#11–#13/M2）、`normalization-and-triage.md`（#14/M2）、`review-approval-workflow.md`（#19/M4）、`external-collector-boundary.md`（#21/M5）、`error-handling.md`（#20/#22）、runbooks（#22/M6）等が、確定 Milestone と追跡 Issue 付きで特定できる

### Requirement: SharePoint publishing unresolved items consolidate to issue #2

SharePoint 投稿方式・お知らせ掲示板 contract に関する未決事項は、Issue #2 に集約され、中央レビューマトリクスから参照可能でなければならない（SHALL）。本レビューは #2 の contract 判断（List item か Site Page か、Graph 権限、公開範囲、添付の扱い等）自体を決定してはならない（SHALL NOT）。route のみを行う。

#### Scenario: SharePoint 未決事項から #2 へ辿れる
- **WHEN** SharePoint 投稿方式の未決事項（News promote、添付・画像、公開範囲、delegated/application/managed identity 等）を確認する
- **THEN** 中央マトリクスおよび `sharepoint-publishing.md` / sharepoint ADR / `graph-authentication.md` の Related Issues から #2 に集約されていることが分かる

### Requirement: LLM provider strategy unresolved items consolidate to issue #15

LLM provider 戦略（production/test provider 分離、provider 契約、入力データ制限、provider 切替方針）の未決事項は、Issue #15 に集約され、中央レビューマトリクスから参照可能でなければならない（SHALL）。本レビューは #15 の provider 戦略自体を決定してはならない（SHALL NOT）。route のみを行う。

#### Scenario: LLM provider 未決事項から #15 へ辿れる
- **WHEN** LLM provider 戦略の未決事項を確認する
- **THEN** 中央マトリクスおよび `llm-provider.md` / `security-baseline.md` / llm-provider-strategy ADR の参照から #15 に集約されていることが分かる

### Requirement: Implementation-before-spec gaps are issue-tracked without speculative issues

実装前に必要な Spec の不足は、既存の追跡 Issue に紐づけられていることをレビューで確認・記録しなければならない（SHALL）。M0 で未確定の spec 不足（SharePoint contract=#2、security/secrets/audit/compliance baseline=#5、Graph auth model=#27）が既存 Issue で追跡されていることを中央マトリクスに記録しなければならない（SHALL）。既存 Issue が gap を明確に表している場合は新規 Issue を作成してはならない（SHALL NOT）。投機的な Issue を作成してはならない（SHALL NOT）。

#### Scenario: spec 不足が既存 Issue で追跡されている
- **WHEN** 実装前に必要な spec 不足を確認する
- **THEN** 各 gap が既存 Issue（M0 spec: #2 / #5 / #27、後続 spec: #11–#22 / #32–#36）に紐づいていることが中央マトリクスから分かり、新規の投機的 Issue は作成されていない

### Requirement: Central review matrix is the canonical review record

詳細設計文書レビューの中央レビュー記録は `docs/design-documents.md` の Review & Status Matrix としなければならない（SHALL）。フィールド表・spec 本文・長大な仕様テキストを別文書に複製してはならない（SHALL NOT）。各文書の M0 disposition は、この中央マトリクスを単一の正本として参照可能でなければならない（SHALL）。

#### Scenario: 中央マトリクスを単一正本として参照する
- **WHEN** 設計文書セット全体の M0 における位置づけを確認する
- **THEN** `docs/design-documents.md` の Review & Status Matrix が単一の正本であり、各文書の status・確定 Milestone・追跡 Issue・未決事項の route 先がそこから一覧でき、フィールド表や spec 本文の複製がない
