## Why

Issue #22 requires the production hardening documentation needed before SPAutoPost is operated with real Microsoft Graph, LLM provider, scheduler, audit log, and SharePoint publishing paths. Existing security and operation specs define the baseline, but M6 needs an operator-facing checklist that ties runbook, retry/backoff/rate-limit policy, secret contamination checks, permission review, observability, audit review, and security review into one pre-production workflow.

## What Changes

- Add a production hardening runbook that centralizes the M6 pre-production checks.
- Document retry/backoff/rate-limit handling for source collection, LLM providers, and Microsoft Graph publishing.
- Document secret contamination checks for repository content, generated artifacts, logs, configs, and CI.
- Document Microsoft Graph and LLM provider permission/data-handling review steps.
- Document observability and audit log review steps before production enablement.
- Extend the existing operation and security review runbooks with concrete cross-links to the production hardening workflow.
- Do not change application code, external API behavior, credentials, CI policy, or publishing behavior.

## Capabilities

### New Capabilities

- `production-hardening`: Operator-facing production hardening documentation and checklist for Issue #22 / M6.

### Modified Capabilities

- なし。

## Impact

- `docs/runbooks/production-hardening.md`
- `docs/runbooks/operation.md`
- `docs/runbooks/security-review.md`
- `README.md`
- `docs/design-documents.md`
- `openspec/changes/issue-22-production-hardening-runbook-observability-security-review/`
