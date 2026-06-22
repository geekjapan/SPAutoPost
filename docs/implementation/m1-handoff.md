# M1 Implementation Handoff

## Purpose

This document is the handoff note for implementation agents working on SPAutoPost M1.

M1 is not a manual-input-only demo. M1 must prove the practical vertical slice:

```text
minimal source intake
  -> Advisory
  -> DraftPost generation
  -> PostgreSQL persistence
  -> Admin UI/API review and edit
  -> approval / confirmation
  -> dedicated SharePoint Site Page / News posting
  -> Publication and AuditEvent records
```

## Repository

```text
geekjapan/SPAutoPost
```

## Canonical References

Implementation agents must read these first:

```text
README.md
AGENTS.md
docs/project-rules.md
docs/specs/m1-mvp-scope.md
docs/specs/architecture.md
docs/specs/data-model.md
docs/specs/configuration.md
docs/specs/admin-ui-api.md
docs/specs/deployment.md
docs/specs/sharepoint-publishing.md
docs/specs/graph-authentication.md
docs/specs/admin-authentication.md
docs/decisions/2026-06-22-m1-implementation-order.md
docs/decisions/2026-06-22-storage-strategy.md
docs/decisions/2026-06-22-admin-ui-stack.md
docs/decisions/2026-06-22-db-migration-strategy.md
```

When these documents conflict with implementation assumptions, the documents win.

## M1 Completion Criteria

M1 is complete when all of the following are true:

1. A minimal source intake or search flow can create a posting candidate.
2. The candidate can be converted into an Advisory.
3. A DraftPost can be generated automatically from the Advisory.
4. Advisory, DraftPost, ReviewEvent, Publication, and AuditEvent are persisted in PostgreSQL.
5. TypeScript / Node.js Admin UI/API can list and show DraftPost records.
6. An administrator can edit, approve, reject, or request regeneration.
7. An approved DraftPost can be posted to the dedicated SharePoint Site Page / News target.
8. Publication and AuditEvent records are written for posting attempts and results.
9. Azure Container Apps / Jobs deployment skeleton exists.

## Implementation Order

M1 must be implemented in this order:

```text
1. PostgreSQL schema / migration baseline
2. Python core source and draft pipeline
3. TypeScript / Node.js Admin UI/API
4. Graph / SharePoint posting PoC
5. Azure Container Apps / Jobs deployment skeleton
```

Optional spikes must not block the main line.

Optional spikes:

```text
- Firecrawl source adapter evaluation
- optional LLM draft provider evaluation
- Foundry / Azure OpenAI provider spike
- generic LLM API provider spike
```

## First Issue to Start

Start with:

```text
#28 [M1][Change] Implement PostgreSQL storage baseline
```

Expected first OpenSpec change:

```text
issue-28-implement-postgresql-storage-baseline
```

## Phase 1: PostgreSQL schema / migration baseline

Primary issues:

```text
#3  Define canonical advisory, draft, and publication data model
#28 Implement PostgreSQL storage baseline
```

Expected outcome:

```text
- PostgreSQL schema baseline
- migration baseline under db/migrations or equivalent
- storage port / repository boundary
- tables or equivalent structures for Advisory, DraftPost, ReviewEvent, Publication, AuditEvent
- idempotency key support
- local/test SQLite adapter or explicit follow-up issue
```

## Phase 2: Python core source and draft pipeline

Primary issues:

```text
#7  Implement manual advisory input and validation
#8  Implement draft composition template for SharePoint announcements
#33 Implement sample source job
#35 Evaluate optional LLM draft providers
```

Expected outcome:

```text
- sample source job or minimal source intake
- Advisory conversion
- DraftPost generation
- deterministic template or mock provider
- AuditEvent records for source intake and draft generation
- optional LLM provider work only if it does not block M1
```

## Phase 3: TypeScript / Node.js Admin UI/API

Primary issues:

```text
#26 Define TypeScript Node.js Admin UI/API boundary
#29 Implement Entra ID login for Admin API/UI
#31 Implement TypeScript Node.js Admin UI API skeleton
```

Expected outcome:

```text
- TypeScript / Node.js Admin UI/API skeleton
- DraftPost list and detail
- draft edit flow
- approve / reject / request regeneration actions
- publish request action
- minimal AuditEvent view
- Microsoft Entra ID login integration or clear local-dev substitute
```

## Phase 4: Graph / SharePoint posting PoC

Primary issues:

```text
#9  Implement SharePoint connector proof-of-concept
#20 Implement SharePoint publish idempotency and state tracking
#32 Implement local Graph delegated posting PoC
#36 Implement approved publish to dedicated SharePoint News
```

Expected outcome:

```text
- local Graph posting PoC may use delegated permission
- approved DraftPost only can be posted
- dedicated SharePoint Site Page / News target
- Publication record for attempts and results
- AuditEvent record for approval and publish result
- idempotency guard
- dry-run mode that does not post
```

## Phase 5: Azure Container Apps / Jobs deployment skeleton

Primary issues:

```text
#24 Finalize Azure hosted core architecture
#25 Add Azure Container Apps deployment skeleton
```

Expected outcome:

```text
- container image skeleton for Python core jobs
- container image skeleton for TypeScript / Node.js Admin UI/API
- Azure Container Apps / Jobs deployment skeleton
- PostgreSQL connection configuration
- environment variable and secret-reference pattern
- GitHub Actions or equivalent build skeleton
```

## Non-Goals for M1

Do not expand M1 to include:

```text
- high-accuracy collection
- full NVD / MyJVN / KEV / vendor adapter completion
- full crawler platform
- production-grade Foundry provider completion
- production hosted Graph authentication finalization
- full Log Analytics integration
- complex multi-step approval workflow
- Teams notification
- ITSM integration
- multi-site publishing
- image / attachment-heavy page layout
```

## Important Rules

- GitHub Issues and Specs are canonical.
- Create an OpenSpec change before implementation for each issue.
- Do not silently change product scope.
- Do not store secrets in repository files, fixtures, logs, or examples.
- Do not implement unattended posting without human approval.
- Do not let optional spikes block the M1 main line.
- Keep Python core, TypeScript / Node.js Admin UI/API, and PostgreSQL boundaries explicit.

## Recommended Codex / Claude Code Prompt

```text
Target repository: geekjapan/SPAutoPost

Start M1 implementation.

Read first:
- README.md
- AGENTS.md
- docs/project-rules.md
- docs/specs/m1-mvp-scope.md
- docs/implementation/m1-handoff.md

Begin with Issue #28.
Create an OpenSpec change named:
issue-28-implement-postgresql-storage-baseline

Follow the M1 implementation order exactly:
1. PostgreSQL schema / migration baseline
2. Python core source and draft pipeline
3. TypeScript / Node.js Admin UI/API
4. Graph / SharePoint posting PoC
5. Azure Container Apps / Jobs deployment skeleton

Do not expand M1 beyond the documented scope.
Optional spikes must not block the main line.
```
