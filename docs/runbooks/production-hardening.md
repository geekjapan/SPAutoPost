# Production Hardening Runbook

## Status

Draft

## Purpose

この runbook は、Issue #22 / M6 で SPAutoPost を本番相当運用に近づける前の確認手順を定義します。実 Secret 登録、Graph 権限付与、LLM provider 契約判断、publish 有効化はこの文書だけで承認された扱いにしません。

## Scope

対象:

- runbook readiness
- retry / backoff / rate limit policy
- observability
- audit log review
- secret contamination check
- Microsoft Graph permission review
- LLM provider permission / data-handling review
- production security review checklist
- incident response readiness

非対象:

- SOC / SIEM 連携の本格実装
- HA / DR の本格設計
- 投稿（publish）有効化の人間承認
- 外部 provider 契約や法務判断そのもの

## Pre-Production Gate

- [ ] `docs/runbooks/operation.md` の dry-run / publish / stop / correction 手順が対象環境に合う
- [ ] `docs/runbooks/security-review.md` の checklist を実施した
- [ ] `docs/runbooks/incident-response.md` の initial response と emergency stop を確認した
- [ ] real publish は human gate を通す
- [ ] scheduler が意図せず publish path を起動しない
- [ ] findings / accepted risk / remediation issue を Issue または decision record に残した

## Retry, Backoff, and Rate Limit Policy

共通方針:

- retry は bounded にする
- retryable と non-retryable を error_code / retryable で区別する
- 429 / rate-limit header / `Retry-After` がある場合はそれを優先する
- timeout / transient network / 5xx は retryable として扱う
- authentication / authorization / validation / target-not-found は retry しない
- publish retry は idempotency_key と既存 Publication を確認してから実施する
- rate limit 回避や規約回避を目的に並列度を上げない

Source collection:

- `source_rate_limited` は待機後に再試行する
- parser / schema mismatch は source format change として Issue 化する
- 同一 source record の重複取り込みは normalization / dedup guard を確認する

LLM provider:

- `provider_rate_limited` / timeout / 5xx は bounded retry にする
- 4xx、config invalid、output validation failure は reviewer 確認に回す
- retry しても prompt_version と generation_input_hash を追跡できることを確認する

Microsoft Graph / SharePoint publish:

- `graph_rate_limited` / timeout / 5xx は backoff 後に再試行できる
- auth failed / authorization failed / target not found / required field missing は retry しない
- failed Publication を retry する前に SharePoint item/page ID と idempotency_key を確認する
- create retry で重複投稿が起きないことを dry-run または test target で確認する

## Secret Contamination Check

確認対象:

- source code
- docs / runbooks / specs / decisions
- config examples and deployment manifests
- tests and fixtures
- generated artifacts
- CI logs and local command output
- AuditEvent / application logs

禁止値:

- API key
- access token / refresh token
- client secret
- certificate private key
- cookie
- authorization header
- real `.env`
- real tenant / app / site identifiers that are not approved for documentation

最低限のローカル確認:

```bash
git status --short
git diff --check
git grep -n -I -E 'BEGIN (RSA |EC |OPENSSH |PRIVATE )?KEY|access_token|refresh_token|client_secret|Authorization:|Cookie:' -- .
```

利用可能な環境では、gitleaks などの secret scanner と dependency scanner も実行します。検出値が実 Secret の可能性を持つ場合は、値を貼らずに identifier / file / line / hash のみを記録し、revoke / rotate を先に行います。

## Microsoft Graph Permission Review

- [ ] production app registration と development app registration が分離されている
- [ ] delegated / application permission の採否理由が decision record または Issue にある
- [ ] site/list/page の投稿先が config で固定されている
- [ ] tenant 全体権限が必要な場合は理由と代替案が記録されている
- [ ] credential rotation / owner / expiry が記録されている
- [ ] Graph error_code と retryable の扱いが `docs/specs/sharepoint-publishing.md` と矛盾しない
- [ ] test target で dry-run または draft posting evidence が残っている

## LLM Provider Review

- [ ] production provider と test provider が分離されている
- [ ] provider terms / data retention / training use / region / SLA / rate limit を確認した
- [ ] LLM に渡す入力は公開 advisory と必要最小限の文体指示だけである
- [ ] Secret、PII、内部ネットワーク、未公開インシデント、攻撃手順を送らない
- [ ] prompt_version と generation_input_hash を audit log で追跡できる
- [ ] output validation と human review が publish 前に必ず入る
- [ ] ChatGPT / Claude subscription UI の自動操作を使わない

## Observability Review

pre-production dry-run で確認する項目:

- [ ] job / request / draft / publication を correlation_id で追跡できる
- [ ] collect / normalize / generate / review / approve / publish / error の結果が確認できる
- [ ] warning と failure が error_code で分類される
- [ ] retryable / failure_count / target が関連情報として残る
- [ ] logs に Secret / token / cookie / authorization header / raw prompt が出ていない
- [ ] scheduler の成功、失敗、停止が運用者に分かる

## Audit Log Review

確認する event_type:

- source_fetch
- source_parse
- normalize
- triage
- draft_generate
- draft_validate
- review
- approve
- reject
- regenerate
- publish_dry_run
- publish_create
- publish_update
- publish_result
- error

レビュー手順:

1. dry-run の correlation_id を 1 つ選ぶ。
2. 収集から publish_dry_run または error までの AuditEvent を追跡する。
3. `audit_event_id`、`event_type`、`correlation_id`、`result`、`created_at` が欠けていないことを確認する。
4. LLM 経路では prompt_version と generation_input_hash を確認する。
5. publish 経路では target site/list/page、idempotency_key、Publication status を確認する。
6. failure では error_code、error_message、retryable、failure_count を確認する。
7. Secret や不要な個人情報が含まれていないことを確認する。

## Production Security Review Checklist

- [ ] repository に Secret / 実 `.env` / 不要生成物がない
- [ ] config example は `env:` 参照または placeholder のみを使う
- [ ] GitHub Actions permissions が最小化されている
- [ ] dependency lockfile と known vulnerability を確認した
- [ ] Graph permission は最小権限で、投稿先が固定されている
- [ ] LLM provider へ渡すデータと provider 契約条件を確認した
- [ ] approved でない DraftPost は publish できない
- [ ] retry で重複投稿しない
- [ ] audit log と application log に Secret がない
- [ ] incident response の emergency stop を実行できる
- [ ] accepted risk と remediation issue を記録した

## Review Output

レビュー結果は Issue または decision record に残します。

必須項目:

- review date
- reviewer
- environment
- scope
- evidence links
- findings
- risk level
- remediation issue
- accepted risk
- publish enablement approval status

## Escalation

次の場合は publish を有効化せず、人間承認または decision gate に戻します。

- 認証 / 認可 / Secret の方式が未確定
- provider 利用条件、rate limit、データ保持が未確認
- 投稿先や投稿権限が未確定
- audit log 保持期間や閲覧権限が未確定
- security / legal judgment が必要

## Related Docs

- `docs/runbooks/operation.md`
- `docs/runbooks/security-review.md`
- `docs/runbooks/incident-response.md`
- `docs/specs/security-baseline.md`
- `docs/specs/audit-log.md`
- `docs/specs/error-handling.md`
- `docs/specs/sharepoint-publishing.md`
