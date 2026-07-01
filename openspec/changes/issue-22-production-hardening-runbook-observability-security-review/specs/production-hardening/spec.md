## ADDED Requirements

### Requirement: Production hardening runbook exists
The system SHALL provide an operator-facing production hardening runbook for Issue #22 / M6 that identifies the pre-production checks required before real scheduler, LLM provider, Microsoft Graph, audit log, and SharePoint publishing paths are enabled.

#### Scenario: Operator follows M6 hardening checklist
- **WHEN** an operator prepares SPAutoPost for production-like operation
- **THEN** the runbook lists the required checks for runbook readiness, retry/backoff/rate-limit policy, secret contamination, permission review, observability, audit review, and production security review

### Requirement: Retry, backoff, and rate-limit policy is documented
The system SHALL document retry, backoff, and rate-limit handling for external source collection, LLM provider calls, and Microsoft Graph publishing, including retryable and non-retryable failure categories and duplicate-post safeguards.

#### Scenario: Retryable provider failure is reviewed
- **WHEN** a source, LLM provider, or Graph request fails due to timeout, transient network failure, service 5xx, or rate limiting
- **THEN** the runbook directs the operator to use bounded retry/backoff, respect provider rate-limit headers where available, and verify idempotency or duplicate guards before retrying publish paths

### Requirement: Secret contamination check is documented
The system SHALL document secret contamination checks for repository content, generated artifacts, configuration examples, logs, CI output, and review evidence before production enablement.

#### Scenario: Secret exposure is checked before PR or release
- **WHEN** a production hardening PR or release candidate is reviewed
- **THEN** the reviewer can follow documented checks to confirm that API keys, tokens, client secrets, cookies, authorization headers, private keys, and real tenant/site identifiers are not committed or logged

### Requirement: Microsoft Graph and LLM provider review is documented
The system SHALL document Microsoft Graph permission review and LLM provider data-handling review before production enablement.

#### Scenario: External provider permissions are reviewed
- **WHEN** real Microsoft Graph or LLM provider credentials are introduced outside the repository
- **THEN** the runbook requires review of least-privilege Graph permissions, production/development app separation, SharePoint target restriction, LLM input minimization, provider terms, and provider-specific rate limits

### Requirement: Observability and audit log review steps are documented
The system SHALL document observability and audit log review steps for dry-run, generation, review, approval, publish, and error paths, including Azure Log Analytics workspace, diagnostic settings, query, and alert verification before production enablement.

#### Scenario: Dry-run evidence is reviewed
- **WHEN** an operator runs a pre-production dry-run
- **THEN** the runbook requires correlation_id tracing, expected AuditEvent event types, error_code/retryable review, Log Analytics query and alert verification, absence of secrets in logs, and preservation of issue or decision-record evidence

### Requirement: Production security review checklist is documented
The system SHALL provide a production security review checklist covering repository hygiene, configuration, secrets, Microsoft Graph, LLM provider use, publishing safety, audit log, observability, CI/CD, incident response, and accepted-risk recording.

#### Scenario: Security review produces an auditable result
- **WHEN** production security review is completed
- **THEN** the result records reviewer, date, scope, findings, risk level, remediation issues, accepted risk, and whether human approval is required before publishing is enabled
