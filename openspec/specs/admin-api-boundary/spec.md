# admin-api-boundary Specification

## Purpose
Admin UI/API（TypeScript/Node）と Python core の M1 境界を定義する。
Admin API は read を PostgreSQL 直読み、write を AdminCommand enqueue に限定し、
Python core が状態遷移、validation、ReviewEvent / AuditEvent 記録、publish 処理を所有する。
## Requirements
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

### Requirement: state-changing request は client Idempotency-Key を必須にする

Admin API は state-changing な `PATCH` / `POST` 要求に対し、client 供給の `Idempotency-Key` を必須にしなければならない（SHALL）。Admin API は route / draft / command type と client key から保存用の AdminCommand `idempotency_key` を導出してよい（MAY）。client key が無い状態変更要求を受け付けてはならない（MUST NOT）。

#### Scenario: client key による retry 重複吸収
- **WHEN** client が同一 `Idempotency-Key` で同一操作を再送する
- **THEN** Admin API は新規 command を二重生成せず、既存 command の status を返す

#### Scenario: client key が無い状態変更要求を拒否する
- **WHEN** client が `Idempotency-Key` 無しで approve / edit / publish-request を要求する
- **THEN** Admin API は AdminCommand を作成せず、validation error を返す

### Requirement: command status read path

Admin API は非同期 reviewer UX のため、AdminCommand の status / error_code / error_message を read できる endpoint を提供しなければならない（SHALL）。command status read は状態を変更してはならない（MUST NOT）。

#### Scenario: command status を取得する
- **WHEN** 管理者が accepted/pending 応答に含まれる command_id の status を要求する
- **THEN** Admin API は pending / processing / succeeded / failed / cancelled と error details を返す
