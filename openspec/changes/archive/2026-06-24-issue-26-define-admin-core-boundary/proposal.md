## Why

M1 では、生成された DraftPost を管理者が確認・修正・承認し SharePoint へ投稿要求する運用が中核になる。その Admin UI/API（TypeScript/Node）と Python core の呼び出し境界は `architecture.md` の Open Question（process / HTTP / shared DB）として未決だった。ADR `admin-core-boundary.md` で境界が決定したため、これを spec として確定し、#31 Admin API skeleton と #28 storage baseline が同じ契約で実装できるようにする。

## What Changes

- 新 capability `admin-api-boundary` を導入し、Admin（TS）↔ Python core の M1 境界を定義する。
- Read は Admin API が PostgreSQL を直読み（DraftPost / ReviewEvent / AuditEvent の一覧・詳細・audit 参照）。
- 状態遷移 Write（approve / reject / request-regeneration / edit / publish-request）は Admin API が auth/RBAC + リクエスト形式 validation のみ行い、idempotent な AdminCommand を1件 insert して accepted/pending を返す。
- Python core/job が pending command を消費し、状態遷移・validation・ReviewEvent・AuditEvent を実行する。
- reviewer UX は非同期（accepted/pending → succeeded/failed）。M1 では同期成功/失敗フィードバックと long-running Python HTTP サービスを設けない。
- `docs/specs/admin-ui-api.md` を本境界に整合させる。

## Capabilities

### New Capabilities
- `admin-api-boundary`: Admin UI/API（TS）と Python core の M1 呼び出し境界。read-direct / write-via-AdminCommand 非同期 handoff、責務分担（TS=auth/RBAC/形式 validation/enqueue、Python=遷移/validation/ReviewEvent/AuditEvent）、accepted/pending UX。

### Modified Capabilities
<!-- 既存 capability spec は未作成のため、変更対象なし。AdminCommand の永続化は storage capability（issue-28）が定義し、本 change はそれを契約として参照する。 -->

## Impact

- 実装契約: #31 Admin API skeleton は write を AdminCommand enqueue に限定し read は直読み。
- 依存: #28 storage capability が AdminCommand テーブルと command queue 操作を提供する（本 change はその契約を前提とする）。
- ドキュメント: `docs/specs/admin-ui-api.md` を更新。
- 正本参照: ADR `admin-core-boundary.md`、`docs/specs/architecture.md`（Open Question を解消）。
- 非対象: 本格 RBAC、同期フィードバック、Graph 認証（#27）、Entra role mapping（#29）。
