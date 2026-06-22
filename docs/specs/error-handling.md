# Error Handling Specification

## Status

Proposed

## Purpose

この Spec は、SPAutoPost の外部 API、LLM provider、SharePoint 投稿、収集処理、正規化処理、レビュー/承認処理で発生するエラーの分類、retry/backoff、監査記録、停止条件を定義します。

## Error Model

推奨 fields:

- error_code
- message
- retryable
- severity
- component
- correlation_id
- related_id
- occurred_at

severity:

- critical
- error
- warning
- info

## Error Categories

### Source Errors

- source_auth_failed
- source_rate_limited
- source_timeout
- source_unavailable
- source_response_invalid
- parser_failed
- normalization_failed

### LLM Errors

- provider_config_invalid
- provider_auth_failed
- provider_rate_limited
- provider_timeout
- provider_response_invalid
- provider_output_validation_failed
- provider_policy_blocked

### SharePoint Errors

- graph_authentication_failed
- graph_authorization_failed
- target_site_not_found
- target_list_not_found
- required_field_missing
- graph_rate_limited
- graph_timeout
- publish_failed
- duplicate_detected

### Workflow Errors

- draft_not_approved
- invalid_state_transition
- review_required
- idempotency_conflict

### Configuration Errors

- config_file_missing
- config_invalid
- secret_missing
- unknown_provider
- unsafe_publish_enabled

## Retry Policy

Retryable:

- timeout
- temporary unavailable
- rate limited
- transient Graph error
- transient provider error

Non-retryable:

- authentication failed
- authorization failed
- config invalid
- required field missing
- invalid state transition
- output validation dangerous detail

## Backoff

推奨:

- exponential backoff
- jitter
- max retry count
- rate limit header を尊重できる場合は尊重する

MVP では単純な retry count と sleep でもよいが、retry により重複投稿しないことを必須とします。

## Partial Failure

複数 Advisory を処理する場合:

- 1 件の失敗で全体を止めるかは mode で制御する
- failed advisory は error として記録する
- publish 失敗は draft 単位で隔離する
- partial success は AuditEvent に記録する

## Stop Conditions

次の場合は処理を止めます。

- Secret 不足
- unsafe publish config
- Graph authorization failed
- provider policy blocked
- dangerous output detected
- approved でない draft の publish attempt
- idempotency conflict

## User-Facing Error Message

利用者に見せる error は、Secret や内部詳細を含めません。

例:

```text
SharePoint 投稿に失敗しました。権限または投稿先設定を確認してください。correlation_id=...
```

## Audit Requirements

全 error は AuditEvent に記録します。

必須:

- error_code
- component
- retryable
- correlation_id
- timestamp

禁止:

- token
- client secret
- raw authorization header
- raw prompt with sensitive data

## Related Issues

- #10 Implement dry-run preview and minimal audit log
- #20 Implement SharePoint publish idempotency and state tracking
- #21 Add scheduler and external collector import boundary
- #22 Production hardening runbook, observability, and security review
