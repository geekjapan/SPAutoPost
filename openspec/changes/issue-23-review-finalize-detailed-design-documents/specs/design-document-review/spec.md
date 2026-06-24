## ADDED Requirements

### Requirement: Central review matrix covers Issue #23 target documents

`docs/design-documents.md` SHALL include a central review matrix for the document set listed in GitHub Issue #23. The matrix SHALL preserve each document's current Status while adding the Issue #23 review result needed for M0 planning.

#### Scenario: Issue #23 target document is reviewed
- **WHEN** an implementation agent opens `docs/design-documents.md`
- **THEN** the agent can see every Issue #23 target document with its current status, M0 review result, deferred milestone if any, and related follow-up Issue references

### Requirement: M0 accepted and near-accepted documents are identified

The central review matrix SHALL identify documents that are Accepted or near-Accepted for M0 foundation use. Near-Accepted SHALL mean the document is usable for implementation orientation while one or more scoped follow-up Issues still own remaining details.

#### Scenario: M0 planning needs a usable design source
- **WHEN** an agent needs to know which design documents can guide M0 / M1 implementation
- **THEN** the matrix distinguishes Accepted / near-Accepted documents from documents deferred to later milestones

### Requirement: M1+ deferred documents are identified

The central review matrix SHALL identify documents whose detailed acceptance belongs to M1 or later milestones. Each deferred row SHALL link existing follow-up Issues when the owner is already clear.

#### Scenario: Later milestone detail is not decided in M0
- **WHEN** a design detail belongs to M1 or later
- **THEN** the matrix records that the document is deferred and points to the existing Issue rather than deciding the detail in Issue #23

### Requirement: SharePoint unresolved decisions route to Issue #2

SharePoint publishing and board-contract unresolved decisions SHALL be routed to GitHub Issue #2. This change SHALL NOT decide the remaining SharePoint board contract, Graph permission, draft / publish, publish / promote, attachment, image, or publication-scope details.

#### Scenario: SharePoint publishing open question is found
- **WHEN** the matrix or target document mentions unresolved SharePoint publishing details
- **THEN** the follow-up route is Issue #2, with implementation Issues such as #9, #20, or #36 referenced only when already applicable

### Requirement: LLM strategy unresolved decisions route to Issue #15

LLM provider strategy unresolved decisions SHALL be routed to GitHub Issue #15. This change SHALL NOT decide production provider selection, test provider policy beyond existing docs, provider contract, cost, UI automation, or production data handling.

#### Scenario: LLM provider strategy open question is found
- **WHEN** the matrix or target document mentions unresolved LLM provider strategy details
- **THEN** the follow-up route is Issue #15, with implementation or spike Issues such as #6, #18, or #35 referenced only when already applicable

### Requirement: Implementation-before-spec gaps link existing Issues only

The review matrix SHALL identify implementation-before-spec gaps only when they can be tied to existing GitHub Issues. This change SHALL NOT create speculative follow-up Issues.

#### Scenario: Existing implementation precedes final spec acceptance
- **WHEN** a target document has related implementation work that is already complete or in progress before the document is fully Accepted
- **THEN** the matrix links the existing Issue that owns reconciliation or follow-up, and does not invent a new Issue
