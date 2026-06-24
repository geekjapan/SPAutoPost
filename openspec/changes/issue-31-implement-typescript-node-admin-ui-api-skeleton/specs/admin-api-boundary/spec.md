## MODIFIED Requirements

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
