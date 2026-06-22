# Admin API / UI in M1

## Status

Accepted

## Context

SPAutoPost の運用では、定期収集で作成された記事を管理者が確認し、必要に応じて修正し、確定後に SharePoint Site Page / News として投稿します。

CLI / Batch だけでも初期検証は可能ですが、Azure hosted core を前提にする場合、管理者レビュー、修正、承認、投稿要求の操作を UI/API として早期に提供する方が運用に近い検証になります。

## Decision

Admin API / UI の最小境界を M1 に含めます。

M1 で含める最小機能:

- DraftPost 一覧
- DraftPost 詳細
- validation warning 表示
- DraftPost の修正
- approve / reject / request regeneration
- publish request または publish-approved job への引き渡し
- AuditEvent の最小参照

## Rationale

- 定期収集・記事生成の運用では、生成済み記事を人間が確認する操作が中核になる。
- CLI のみでは、管理者確認・修正・承認の運用イメージを検証しにくい。
- 早期に UI/API 境界を作ることで、Python core と TypeScript / Node.js layer の責務分離を確認できる。

## Consequences

- #26 を M1 の設計 Issue として扱う。
- M1 の MVP 範囲に Admin API / UI の skeleton を含める。
- 本格的な多人数 RBAC、通知、複雑なワークフローは M1 対象外とする。
- UI/API の実装言語は TypeScript / Node.js を候補とするが、最小 API を Python 側で先に実装するかは #26 で決める。

## Related

- Spec: docs/specs/architecture.md
- Spec: docs/specs/review-approval-workflow.md
- Issue: #19
- Issue: #26
