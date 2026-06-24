## ADDED Requirements

### Requirement: M0 Accepted document set is identified

Detailed design document review (Issue #23) SHALL identify the document set accepted for M0 in the central review matrix. The M0 Accepted set SHALL include only documents whose core decision is already backed by an Accepted ADR or merged/archived OpenSpec change and does not require a human-gated decision. At minimum, it SHALL identify `docs/specs/sharepoint-publishing.md` (MVP publishing mode backed by Accepted ADR `2026-06-22-sharepoint-list-vs-site-page.md`; remaining details route to #2), `docs/specs/data-model.md` (#3), `docs/specs/configuration.md` (#4), and `docs/decisions/2026-06-22-sharepoint-list-vs-site-page.md` as M0 Accepted. Documents whose core decision still depends on an open owning Issue, such as security/secrets/audit baseline (#5), LLM provider strategy (#15), and Graph auth model (#27), SHALL NOT be flipped to M0 Accepted before that Issue is resolved.

#### Scenario: M0 Accepted documents are found from the central matrix
- **WHEN** an implementation agent checks which design documents are accepted for M0
- **THEN** the agent can identify the M0 Accepted set from `docs/design-documents.md` and see that the document status labels are consistent with the matrix buckets

### Requirement: M1+ deferred document set is identified

The review SHALL identify Proposed, Draft, or Deferred documents whose detailed acceptance belongs to M1 or later milestones. Each M1+ document SHALL be mapped to its owning milestone and existing tracking Issues in the central matrix.

#### Scenario: Later-milestone documents have tracked owners
- **WHEN** an implementation agent checks which design documents are finalized after M0
- **THEN** the matrix identifies documents such as `llm-provider.md` (#15/M3), `draft-composition.md` (#8/M3), `source-collection.md` (#11-#13/M2), `normalization-and-triage.md` (#14/M2), `review-approval-workflow.md` (#19/M4), `external-collector-boundary.md` (#21/M5), `error-handling.md` (#20/#22), and runbooks (#22/M6), each with milestone and Issue routing

### Requirement: SharePoint remaining unresolved items consolidate to Issue #2

SharePoint board-contract unresolved items SHALL be routed to Issue #2 and visible from the central review matrix. The review SHALL NOT reopen the already accepted MVP decision to use SharePoint Site Page / News instead of SharePoint List item as the primary posting mode. The review SHALL NOT decide the remaining #2 contract details; it SHALL only route them.

#### Scenario: SharePoint remaining open items route to #2
- **WHEN** an implementation agent checks remaining SharePoint open items such as News promote, attachments/images, publication scope, Graph permissions, delegated/application/managed identity, or failure behavior
- **THEN** the central matrix and the related `sharepoint-publishing.md`, sharepoint ADR, and `graph-authentication.md` references route those remaining items to Issue #2 while preserving Site Page / News as the accepted MVP posting mode

### Requirement: LLM provider strategy unresolved items consolidate to Issue #15

LLM provider strategy unresolved items, including production/test provider separation, provider contracts, input-data restrictions, and provider switching policy, SHALL route to Issue #15 and be visible from the central matrix. This review SHALL NOT decide the Issue #15 provider strategy; it SHALL only route it.

#### Scenario: LLM provider unresolved items route to #15
- **WHEN** an implementation agent checks LLM provider strategy open items
- **THEN** the central matrix and the related `llm-provider.md`, `security-baseline.md`, and LLM provider strategy ADR references route them to Issue #15

### Requirement: Implementation-before-spec gaps are issue-tracked without speculative issues

The review SHALL confirm and record that spec gaps needed before implementation are tied to existing tracking Issues. M0 unresolved spec gaps (SharePoint remaining contract #2, security/secrets/audit/compliance baseline #5, Graph auth model #27) SHALL be recorded in the central matrix. When an existing Issue clearly represents a gap, the review SHALL NOT create a new Issue. The review SHALL NOT create speculative Issues.

#### Scenario: Spec gaps are tracked by existing Issues
- **WHEN** an implementation agent checks spec gaps needed before implementation
- **THEN** each gap is traceable from the central matrix to existing Issues (M0 spec: #2 / #5 / #27; later specs: #11-#22 / #32-#36), and no speculative Issue is created

### Requirement: Central review matrix is the canonical review record

The central review record for detailed design document review SHALL be `docs/design-documents.md`'s Review & Status Matrix. The review SHALL NOT duplicate field tables, spec bodies, or long specification text into a second document. Each document's M0 disposition SHALL be available from this central matrix as the single review record.

#### Scenario: Central matrix is used as the single review record
- **WHEN** an implementation agent checks the overall M0 disposition of the design document set
- **THEN** `docs/design-documents.md`'s Review & Status Matrix is the single review record listing each document's status bucket, owning milestone, tracking Issues, and route target without duplicating spec bodies
