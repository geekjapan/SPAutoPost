## ADDED Requirements

### Requirement: Container Apps and Jobs logs are confirmable in Log Analytics
The system SHALL document how operators confirm that SPAutoPost Azure Container Apps apps and Container Apps Jobs send console and system logs to the selected Log Analytics workspace.

#### Scenario: Operator confirms hosted logs
- **WHEN** an operator opens the Log Analytics workspace for the SPAutoPost Container Apps Environment
- **THEN** the documented query can find recent Admin API app logs and scheduled job logs without requiring tenant-specific resource names in the repository

### Requirement: AuditEvent correlation_id is traceable
The system SHALL provide a Log Analytics query path for `AuditEvent` JSON log lines that filters by `correlation_id` and shows `event_type`, `result`, `error_code`, operation, and publication identifiers.

#### Scenario: Incident investigation follows a correlation_id
- **WHEN** an operator has a `correlation_id` from an incident, Admin API response, or AuditEvent
- **THEN** the documented query returns matching audit events ordered by time

### Requirement: error_code and publication result are searchable
The system SHALL provide Log Analytics query snippets to search `error_code` values and publication result events, including failed and skipped publication attempts.

#### Scenario: Operator searches publication failures
- **WHEN** an operator investigates SharePoint publication failures
- **THEN** the documented query returns publication `result`, `error_code`, `operation`, `idempotency_key`, and SharePoint page identifiers when present

### Requirement: Secret and token redaction is confirmable
The system SHALL provide a Log Analytics confirmation query that searches SPAutoPost logs for token, secret, cookie, authorization header, and private key indicators, and SHALL require any hit to be treated as a security finding until proven to be a placeholder or false positive.

#### Scenario: Security reviewer checks redaction
- **WHEN** a security reviewer runs the documented redaction query against production-like logs
- **THEN** no access token, refresh token, client secret, cookie, authorization header, private key, or raw credential value is returned

### Requirement: Tenant-specific provisioning remains manual
The system SHALL NOT commit tenant-specific Log Analytics workspace IDs, diagnostic setting resource IDs, alert destinations, dashboard IDs, or real Azure resource names. These values SHALL be filled by the operator during Azure setup and recorded outside the repository or in approved environment-specific configuration.

#### Scenario: Repository examples contain placeholders only
- **WHEN** the repository examples are inspected
- **THEN** they contain placeholders and manual steps, not real workspace IDs or secrets
