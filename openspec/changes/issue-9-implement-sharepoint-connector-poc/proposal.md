## Why

Issue #9 (Milestone M1) needs a working proof-of-concept that publishes an approved `DraftPost` to a SharePoint Site Page / News target through Microsoft Graph. The data model (`Publication`, `AuditEvent`), the dry-run preview (`spautopost.dry_run`), and the SharePoint/Graph specs are in place, but there is no connector that actually initializes a Graph client, builds the Site Page payload, posts it, and records the result. The `#27` authentication decision (`docs/specs/graph-authentication.md`) selects **delegated permission for the local PoC**, so this connector targets delegated auth while keeping the hosted-runtime (managed identity / app-only) path out of scope.

## What Changes

- Add `spautopost.sharepoint_connector` with an **injectable Graph transport** (default stdlib `urllib`, HTTPS-only) and an **injectable delegated token provider** (`Callable[[], str]`), so unit tests never call live Graph and never need a real token.
- Create a SharePoint **Site Page draft** from an approved `DraftPost`: render the `draft-composition` sections into an HTML text web part (`html.escape`-d), build the Microsoft Graph `sitePage` create payload, and `POST /sites/{site-id}/pages`.
- Enforce the publish precondition: a draft whose status is not `approved` is rejected with `draft_not_approved` and never reaches Graph (a stop condition per `error-handling.md`).
- **Dry-run mode**: when enabled, build the Publication/AuditEvent records and perform **no** Graph write at all.
- Record the outcome as a `Publication` (+ append an `AuditEvent`) via the existing `StoragePort` when one is supplied; without a store the connector returns the DTOs for the caller to persist.
- Compute a **deterministic idempotency key** (`draft_id` + target site / page library + sorted `advisory_ids` + normalized title hash) and, when a store is supplied, skip re-posting when a `published`/`publishing` Publication already exists (`duplicate_detected`).
- Classify Graph failures into the canonical `error-handling.md` SharePoint codes (`graph_authentication_failed` 401, `graph_authorization_failed` 403, `target_site_not_found` 404, `graph_rate_limited` 429, transient `graph_timeout` on 5xx/network) with `retryable`, and record them instead of crashing.
- **Secret hygiene**: the delegated token appears only in the `Authorization` header; it is never logged, stored, or placed in any `Publication`/`AuditEvent`/error message.
- Add unit tests covering draft create, dry-run no-op, approval guard, each error class, idempotency skip, and token non-leakage.
- **Non-goals**: real delegated sign-in (MSAL device-code flow) and CLI wiring (Issue #32), News promote/publish (`/publish`) and update operations, hosted-runtime managed-identity / app-only auth (#27 follow-ups), attachments/images, complex page layouts, multi-site posting.

## Capabilities

### New Capabilities

- `sharepoint-connector`: delegated-auth Microsoft Graph connector that creates a SharePoint Site Page draft from an approved `DraftPost`, supports dry-run, records `Publication`/`AuditEvent`, enforces idempotency, and classifies Graph errors — all with injectable transport and token provider.

### Modified Capabilities

<!-- No existing OpenSpec capability requirements are modified. -->

## Impact

- **Code**: adds `spautopost.sharepoint_connector`; reuses the existing `Publication`/`AuditEvent` DTOs, `StoragePort`, and `draft-composition` section order. No changes to existing modules.
- **Tests**: adds fixture/fake-transport unit tests; no live network and no real secrets.
- **Runtime / DB**: no migration. Default real transport uses stdlib `urllib` against `https://graph.microsoft.com/v1.0`.
- **Security**: delegated bearer token is injected and sent only as the `Authorization` header — never logged, stored, or committed. Publishing stays gated on `approved` drafts; dry-run performs no write.
- **Auth boundary**: per `#27`, delegated permission is the local PoC method only; hosted runtime (managed identity / app-only) is explicitly deferred.
