## ADDED Requirements

### Requirement: Read は Admin API による直読み

Admin API（TypeScript/Node）は、DraftPost / ReviewEvent / AuditEvent の一覧・詳細・audit 参照を PostgreSQL から直接 read してよい（SHALL）。read 経路はドメイン状態を変更してはならない（MUST NOT）。

#### Scenario: DraftPost 一覧の取得
- **WHEN** 認証済み管理者が DraftPost 一覧を要求する
- **THEN** Admin API は PostgreSQL から直読みして一覧を返し、状態は変更されない

### Requirement: 状態遷移 Write は AdminCommand 経由の非同期 handoff

approve / reject / request-regeneration / edit / publish-request の状態遷移 Write は、Admin API が auth/RBAC とリクエスト形式 validation のみ実施し、idempotent な AdminCommand を1件挿入して accepted/pending を返さなければならない（SHALL）。Admin API がドメイン状態機械を直接更新してはならない（MUST NOT）。

#### Scenario: approve 要求の受付
- **WHEN** 管理者が DraftPost に approve を要求する
- **THEN** Admin API は AdminCommand を1件挿入し、accepted/pending を返す（DraftStatus はまだ変更されない）

#### Scenario: 重複要求の idempotent 処理
- **WHEN** 同一 idempotency_key の AdminCommand 要求が再送される
- **THEN** 重複は新規実行を生まず、既存 command の状態が返る

### Requirement: 遷移実行は Python core が所有

Python core/job は pending AdminCommand を消費し、現在の DraftStatus に対する遷移の妥当性を検証したうえで、状態遷移・validation・ReviewEvent 記録・AuditEvent 記録を実行しなければならない（SHALL）。

#### Scenario: command 消費による状態遷移
- **WHEN** Python worker が approve の pending command を claim する
- **THEN** DraftStatus が approved に遷移し、ReviewEvent と AuditEvent が記録され、command が succeeded になる

#### Scenario: 不正遷移の拒否
- **WHEN** 現在 DraftStatus が approve を許さない状態で approve command を処理する
- **THEN** 遷移は適用されず、command は failed（error_code 付き）になる

### Requirement: 非同期 reviewer UX

M1 の reviewer 操作フィードバックは非同期（accepted/pending → succeeded/failed）でなければならない（SHALL）。同期成功/失敗フィードバックと long-running Python HTTP サービスは M1 では設けない（MUST NOT）。

#### Scenario: pending から結果表示への遷移
- **WHEN** 管理者の操作後、Python worker が command を処理完了する
- **THEN** UI は pending から succeeded または failed の結果を後追いで表示できる

#### Scenario: edit（本文修正）の楽観反映
- **WHEN** 管理者が DraftPost 本文を修正して保存する
- **THEN** Admin API は edit を AdminCommand として enqueue し、UI は楽観反映したうえで pending→saved/failed を後追い表示する（content mutation も Python 所有）

### Requirement: idempotency_key は Admin API server が発番

Admin API は AdminCommand の idempotency_key を server 側で発番しなければならない（SHALL）。client が request-id を供給した場合のみ、それを併用して重複検知を強めてよい（client 供給は任意）。

#### Scenario: server 発番による重複吸収
- **WHEN** client が request-id を供給せずに同一操作を二重送信する
- **THEN** Admin API は server 発番の idempotency_key により重複を吸収し、新規 command を二重生成しない
