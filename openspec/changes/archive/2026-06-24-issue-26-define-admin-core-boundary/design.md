## Context

polyglot 構成（Python core + TS/Node Admin UI/API）が単一 PostgreSQL を共有する M1 で、両者の呼び出し境界が `architecture.md` の Open Question だった。ADR `admin-core-boundary.md`（Opus 4.8 × GPT-5.5 の cross-model 議論で round 1 収束）で「read 直読み / write は AdminCommand 経由の非同期 handoff」に決定済み。本 change はそれを spec 契約として確定する。実装は #31（Admin API）と #28（AdminCommand 永続化）が担う。

## Goals / Non-Goals

**Goals:**
- M1 の Admin↔Python core 境界を testable な spec として固定する。
- #31 と #28 が同一契約で並行実装できるようにする。

**Non-Goals:**
- Admin API/UI の実装そのもの（#31）。
- AdminCommand テーブルの schema 定義（#28 storage capability が所有）。
- 同期フィードバック、本格 RBAC、Graph 認証（#27）、Entra role mapping（#29）。

## Decisions

- **read 直読み / write 非同期 command**。理由: Python core が所有する状態機械を単一の真実に保ち、遷移ロジックを TS に二重実装しない。代替案（Python HTTP サービスで同期処理）は long-running runtime を M1 に足すコストに見合わず却下。
- **責務分担**: TS=auth/RBAC + リクエスト形式 validation + idempotent enqueue。Python=遷移妥当性 + validation + ReviewEvent + AuditEvent。
- **idempotency**: AdminCommand の idempotency_key（command_type + draft + requested_by + client token）で重複要求を吸収。
- **依存方向**: 本 change（契約）は #28（AdminCommand 永続化）に依存する。順序は #28 を先に apply。

## Risks / Trade-offs

- [非同期化により reviewer が即時結果を得られない] → M1 は pending→succeeded/failed の後追い表示で許容（プロダクト判断として確定済み）。同期要件が出た場合は別途設計。
- [read 直読みで TS が schema に結合する] → read は参照のみ・状態不変に限定。書き込み経路を command に一本化し結合面を最小化。
- [契約と実装の乖離] → spec scenario をそのまま #31/#28 のテスト観点に流用して整合を検証。

- **edit（本文修正）も非同期 AdminCommand で扱う**。content mutation も Python 所有とし、UI は楽観反映 + pending→saved/failed で許容（grill R1 で確定）。edit だけ別経路にして境界を2本化しない。
- **idempotency_key / client token は Admin API server が発番**する。client が request-id を供給した場合のみそれを併用して重複検知を強める（client 供給は任意、grill R2 で確定）。

## Open Questions

- なし（R1/R2 は確定済み）。
