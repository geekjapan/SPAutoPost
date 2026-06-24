## Why

Issue #1 is the parent tracking issue for the initial SPAutoPost roadmap. Its acceptance criteria are project-management oriented: GitHub milestones must exist, M0-M6 issues must be assigned, the initial execution order must be agreed, and implementation agents must recognize the OpenSpec change rule.

The repository already has the milestone structure, issue allocation, implementation-order decision records, and agent rules. This change records that evidence in the roadmap so Issue #1 can be closed without changing product behavior.

## What Changes

- Record the Issue #1 completion snapshot in `docs/roadmap.md`.
- Replace the old "recommended GitHub milestones" wording with active milestone tracking wording.
- Link the initial execution order to `docs/decisions/2026-06-22-m1-implementation-order.md`.
- Confirm that `AGENTS.md`, `CLAUDE.md`, `docs/openspec-workflow.md`, and `docs/runbooks/multi-agent-orchestration.md` carry the OpenSpec-first implementation rule.
- **Non-goals**: product scope changes, runtime code, authentication, publishing, external services, secrets, or milestone restructuring.

## Capabilities

### New Capabilities

- `roadmap-index`: records roadmap tracking evidence and initial execution-plan ownership for Issue #1.

### Modified Capabilities

<!-- No existing OpenSpec capability requirements are modified. -->

## Impact

- **Documentation**: `docs/roadmap.md` gains the Issue #1 completion evidence snapshot.
- **OpenSpec**: adds `roadmap-index` capability for the tracking evidence.
- **Runtime / DB / API**: no changes.
- **Security**: no secrets, credentials, tokens, external account actions, or publish behavior.
