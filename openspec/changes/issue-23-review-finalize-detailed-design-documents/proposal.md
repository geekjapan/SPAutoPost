## Why

Issue #23（M0, Docs）は、SPAutoPost の詳細設計文書セット（specs / runbooks / decisions、計 18 文書）をレビューし、M0 で Accepted に近づける文書と、後続 Milestone で確定する文書を整理することを目的とする。設計文書は既に整備済みだが、各文書の M0 における位置づけ（Accepted / Proposed / Draft / Deferred）が一覧で確定しておらず、SharePoint 投稿方式の残未決事項（#2）と LLM provider 戦略の未決事項（#15）の集約先が文書横断で明示されていない。

本 change は、レビュー結論を OpenSpec 上に binding な review policy capability として固定し、`docs/design-documents.md` を中央レビュー記録（Review & Status Matrix）として正本化する。フィールド表や spec 本文は複製せず、既存ドキュメント構造の中央マトリクスに集約する（Issue #23 の指示）。実装コード・認証・Secret・SharePoint 投稿挙動・Azure リソースには一切触れない。

## What Changes

- 新 capability `design-document-review` を追加し、Issue #23 のレビュー結論を binding な不変条件として OpenSpec 上に固定する。
- `docs/design-documents.md` に **Review & Status Matrix (Issue #23)** を追加し、18 対象文書を M0 disposition（Accepted for M0 / M0 finalization tracked by issue / Proposed→M1+ / Draft runbook）で分類する中央レビュー記録とする。
- M0 で finalize 可能な foundational 文書のステータスを更新する: `docs/specs/data-model.md` と `docs/specs/configuration.md` を Proposed → **Accepted for M0** に確定する（前者は #3 で canonical data model が merge 済み、後者は #4 で configuration capability が archive 済みのため、人間ゲート判断を要しない）。
- SharePoint Site Page / News の MVP 投稿方式は Accepted 済みとして維持し、残未決事項（Graph 権限、公開範囲、添付・画像、News promote、投稿失敗時動作など）を **#2** に集約していることを中央マトリクスで明示する。
- LLM provider 戦略の未決事項を **#15** に集約していることを中央マトリクスで明示する（`llm-provider.md`・`security-baseline.md`・llm-provider-strategy ADR の既存参照を一覧化）。
- 認証・Secret・投稿・LLM 契約に依存する文書（`security-baseline.md` #5、`audit-log.md` #5、`graph-authentication.md` #27、各 M1+ spec、ADR）は human-gated のため本 change ではステータスを Accepted に flip せず、最終化を追跡する既存 Issue へ明示的に route する。
- 実装前に必要な Spec 不足は、すべて既存 Issue（M0 spec: #2 / #5 / #27、後続 spec: #11–#22 / #32–#36）で追跡済みであることを確認・記録する。**新規の投機的 Issue は作成しない。**
- **非対象**: 実装コード／DB migration／認証／Secret／SharePoint 投稿挙動／Azure リソース／外部アカウントの変更。#2（SharePoint 残 contract）/ #15（LLM provider 戦略）/ #27（Graph auth model）/ #29（Entra 実装）自体の判断はしない（route のみ）。

## Capabilities

### New Capabilities

- `design-document-review`: Issue #23 の詳細設計文書レビュー結論を binding に固定する。M0 Accepted 文書集合・M1+ Deferred 文書集合の特定、SharePoint 残未決事項の #2 集約、LLM provider 未決事項の #15 集約、Spec 不足の既存 Issue 追跡、中央レビューマトリクスの正本化を規定する。

### Modified Capabilities

<!-- 既存 OpenSpec capability の requirement は変更しない。 -->

## Impact

- **ドキュメント**: `docs/design-documents.md` に Review & Status Matrix を追加し中央レビュー記録とする。`docs/specs/data-model.md`・`docs/specs/configuration.md` の Status を Accepted for M0 に更新する。他文書は status 変更せず、未決事項の route 先を中央マトリクスで明示する。
- **コード**: 変更なし（docs / spec finalization のみ）。
- **テスト**: 変更なし。`openspec validate --strict` を検証手段とする。
- **依存関係**: 追加なし。
- **セキュリティ**: 認証・Secret・投稿・Azure リソースは変更しない。Secret を docs / spec に記載しない。human-gated 文書（security-baseline / audit-log / graph-auth）は flip せず Issue へ route する。
