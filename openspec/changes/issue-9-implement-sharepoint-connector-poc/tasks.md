## 1. Connector implementation
- [x] 1.1 Add `spautopost.sharepoint_connector` with injectable `GraphTransport` (default stdlib `urllib`, HTTPS-only) and `TokenProvider` (`Callable[[], str]`), plus `GraphHttpResponse`/`PublishOutcome` DTOs and a `ConnectorError`/`GraphTransportError` hierarchy.
- [x] 1.2 Render an approved `DraftPost` into an `html.escape`-d Site Page body and build the Microsoft Graph `sitePage` create payload; `POST /sites/{site-id}/pages`.
- [x] 1.3 Enforce the approval precondition (`draft_not_approved`) and required-field precondition (`required_field_missing`) before any Graph call.
- [x] 1.4 Implement dry-run: build `Publication`(`dry_run`)/`AuditEvent`(`publish_dry_run`) with no Graph write.
- [x] 1.5 Compute the deterministic idempotency key and, when a `StoragePort` is supplied, skip re-posting an existing `published`/`publishing` Publication (`duplicate_detected`) and persist via `create_if_absent` + audit `append`.
- [x] 1.6 Classify Graph failures into `error-handling.md` codes (401/403/404/429/5xx/network) with `retryable` and record a `failed` Publication + error `AuditEvent`.
- [x] 1.7 Keep the delegated token in the `Authorization` header only; never log, store, or surface it in any DTO or error message.

## 2. Tests
- [x] 2.1 Successful Site Page draft create: Publication `published`/`create` with `sharepoint_page_id`, AuditEvent `publish_create`.
- [x] 2.2 Dry-run performs no transport call and records `dry_run`.
- [x] 2.3 Non-approved draft raises `draft_not_approved` without calling the transport.
- [x] 2.4 401/403/404/429/5xx/network map to the expected error codes + retryable and record a `failed` Publication.
- [x] 2.5 Idempotency: a second publish of an already-`published` key is skipped (`duplicate_detected`, no transport call).
- [x] 2.6 Token never appears in Publication/AuditEvent/error output; `Authorization` header carries the bearer token.

## 3. Verification
- [x] 3.1 `pytest` (targeted + full with coverage ≥ 80%), `ruff check`/`ruff format --check`, `mypy src`.
- [x] 3.2 `openspec validate issue-9-implement-sharepoint-connector-poc --strict`.
