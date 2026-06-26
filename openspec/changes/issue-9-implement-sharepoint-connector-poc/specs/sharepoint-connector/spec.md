## ADDED Requirements

### Requirement: Connector initializes a delegated Graph client

The SharePoint connector SHALL be constructed with an injectable Graph transport and an injectable delegated token provider (`Callable[[], str]`), so that callers and tests can supply a fake transport and token without any live Microsoft Graph call. The default real transport SHALL use stdlib `urllib` over HTTPS only and SHALL send the delegated bearer token solely in the `Authorization` request header.

#### Scenario: Connector posts with an injected transport and token

- **WHEN** a connector built with a fake transport and a token provider creates a page
- **THEN** the transport receives the request with an `Authorization: Bearer <token>` header and no live Graph endpoint is contacted

#### Scenario: Default transport rejects non-HTTPS URLs

- **WHEN** the default `urllib` transport is asked to call a non-`https://` URL
- **THEN** it raises a transport error without issuing the request

### Requirement: Connector creates a SharePoint Site Page draft from an approved draft

The connector SHALL create a SharePoint Site Page draft from an approved `DraftPost` by rendering the `draft-composition` sections into an HTML text web part and `POST`ing the Microsoft Graph `sitePage` create payload to `/sites/{site-id}/pages`. User-supplied draft text SHALL be HTML-escaped before inclusion in the page body. On success the connector SHALL return a `Publication` with `target_type` `site-page`, `operation` `create`, `publication_status` `published`, and the SharePoint page id.

#### Scenario: Approved draft is created as a Site Page

- **WHEN** an approved `DraftPost` is published through a fake transport returning a created page id
- **THEN** the connector returns a `Publication` with `target_type` `site-page`, `operation` `create`, `publication_status` `published`, the SharePoint page id, and an `AuditEvent` of type `publish_create` / `success`

#### Scenario: Draft body content is HTML-escaped

- **WHEN** a draft whose text contains HTML metacharacters is rendered into the Site Page payload
- **THEN** the metacharacters are escaped in the web part `innerHtml` and not emitted as raw markup

### Requirement: Dry-run performs no Graph write

When dry-run is enabled the connector SHALL NOT call the Graph transport and SHALL record the result as a `Publication` with `publication_status` `dry_run` and `operation` `dry-run`, plus an `AuditEvent` of type `publish_dry_run`.

#### Scenario: Dry-run skips the transport

- **WHEN** an approved draft is published with dry-run enabled
- **THEN** the transport is never called and the returned `Publication` has `publication_status` `dry_run` and `operation` `dry-run`

### Requirement: Connector rejects non-approved drafts

The connector SHALL refuse to publish a `DraftPost` whose status is not `approved`, raising a `draft_not_approved` error before any Graph call, and SHALL refuse a draft missing required content (`required_field_missing`).

#### Scenario: Non-approved draft is rejected before any Graph call

- **WHEN** a draft whose status is not `approved` is submitted for publishing
- **THEN** the connector raises a `draft_not_approved` error and the transport is never called

### Requirement: Connector records the outcome as Publication and AuditEvent

The connector SHALL record every publish attempt as a `Publication` and append an `AuditEvent`. When a storage port is supplied the connector SHALL persist them (race-safe `create_if_absent` for the Publication, append for the AuditEvent); without a store it SHALL return the DTOs for the caller to persist. The `AuditEvent` SHALL carry the approver as `actor` and the publishing identity as `service_principal`.

#### Scenario: Outcome is persisted through the storage port

- **WHEN** a connector with a storage port publishes an approved draft
- **THEN** the Publication is created through `create_if_absent` and the AuditEvent is appended, and the AuditEvent records the approver and publishing identity

### Requirement: Connector classifies and records Graph failures

The connector SHALL classify Graph HTTP failures into the canonical SharePoint error codes — `graph_authentication_failed` (401), `graph_authorization_failed` (403), `target_site_not_found` (404), `graph_rate_limited` (429), and a transient `graph_timeout` for 5xx and network/transport errors — set `retryable` accordingly (auth/authorization/not-found non-retryable; rate-limit/timeout retryable), and record a `failed` `Publication` with an error `AuditEvent` rather than raising. Error messages SHALL NOT contain the token or other secrets.

#### Scenario: Authorization failure is classified and recorded

- **WHEN** the transport returns HTTP 403
- **THEN** the connector records a `failed` Publication with `error_code` `graph_authorization_failed` and `retryable` false, and the error message contains no token

#### Scenario: Rate limiting is retryable

- **WHEN** the transport returns HTTP 429
- **THEN** the connector records a `failed` Publication with `error_code` `graph_rate_limited` and `retryable` true

### Requirement: Connector enforces idempotency to prevent duplicate posts

The connector SHALL compute a deterministic idempotency key from the `draft_id`, target site id, target page library id, sorted `advisory_ids`, and a normalized title hash. When a storage port is supplied and a `Publication` with the same key already exists in `published` or `publishing` state, the connector SHALL skip the Graph call and record `duplicate_detected` rather than posting again.

#### Scenario: Duplicate publish is skipped

- **WHEN** a draft is published whose idempotency key already maps to a `published` Publication in the store
- **THEN** the connector does not call the transport and records the result as `duplicate_detected`

#### Scenario: Idempotency key is deterministic

- **WHEN** the key is computed twice for the same draft, target, advisories, and title
- **THEN** the two keys are identical
