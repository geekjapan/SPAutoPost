## ADDED Requirements

### Requirement: TypeScript Node.js Admin API skeleton

システムは TypeScript / Node.js で Admin API skeleton を提供しなければならない（SHALL）。skeleton は DraftPost list / detail / audit read と、review 系操作の AdminCommand enqueue を扱わなければならない（SHALL）。

#### Scenario: DraftPost list を取得する
- **WHEN** 管理者が `GET /api/drafts` を要求する
- **THEN** Admin API は DraftPost summary 一覧を返し、状態を変更しない

#### Scenario: DraftPost detail を取得する
- **WHEN** 管理者が `GET /api/drafts/{draft_id}` を要求する
- **THEN** Admin API は DraftPost detail と review/audit context を返し、状態を変更しない

### Requirement: AdminCommand enqueue only for writes

Admin API は edit / approve / reject / request-regeneration / publish-request を直接状態遷移として実行せず、AdminCommand を enqueue しなければならない（SHALL）。Admin API は Microsoft Graph 呼び出し、SharePoint 投稿、Python core 状態機械を実行してはならない（MUST NOT）。

#### Scenario: approve を command として受け付ける
- **WHEN** approver が `POST /api/drafts/{draft_id}/approve` を要求する
- **THEN** Admin API は approve AdminCommand を enqueue して accepted/pending と command status URL を返す

#### Scenario: publish request は intent のみを enqueue する
- **WHEN** publisher が `POST /api/drafts/{draft_id}/publish-request` を要求する
- **THEN** Admin API は publish_request AdminCommand を enqueue し、SharePoint 投稿処理は実行しない

### Requirement: Client-supplied idempotency for writes

Admin API は state-changing `PATCH` / `POST` に client 供給の `Idempotency-Key` を要求しなければならない（SHALL）。同一 operation の同一 key 再送は既存 command status を返さなければならない（SHALL）。

#### Scenario: key なし write を拒否する
- **WHEN** 管理者が `Idempotency-Key` なしで approve を要求する
- **THEN** Admin API は AdminCommand を作成せず validation error を返す

#### Scenario: retry を deduplicate する
- **WHEN** 管理者が同一 `Idempotency-Key` で同一 approve request を再送する
- **THEN** Admin API は二重 command を作成せず既存 command を返す

### Requirement: Command status read path

Admin API は非同期 reviewer UX のため、AdminCommand status read path を提供しなければならない（SHALL）。

#### Scenario: pending command status を読む
- **WHEN** 管理者が `GET /api/commands/{command_id}` を要求する
- **THEN** Admin API は command status と error_code / error_message を返す

### Requirement: Development auth boundary

M1 skeleton は本番 Entra ID/OIDC を実装せず、開発用の明示的な principal / role header 境界に限定しなければならない（SHALL）。本番 Entra ID login と role mapping は #29 で扱わなければならない（SHALL）。

#### Scenario: principal header が無い write を拒否する
- **WHEN** 管理者 principal が無い状態で write endpoint を要求する
- **THEN** Admin API は AdminCommand を作成せず authentication error を返す
