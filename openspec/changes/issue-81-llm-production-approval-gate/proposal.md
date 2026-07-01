## Why

Issue #81 records that PR #77, #78, #79, and #80 converged on two approval flags for production LLM providers. The current code already enforces the merged behavior, but `docs/specs/llm-provider.md` and `openspec/specs/llm-provider/spec.md` still describe only the flat flag, so the repo contract is ambiguous.

## What Changes

- Clarify the existing production LLM approval gate model in the LLM provider docs/spec.
- State that `llm.production_approved: true` authorizes production-class providers, while `production_api` can also satisfy startup validation with `llm.azure.production_approved: true`.
- State that this is documentation of the existing gate behavior, not an information-security approval decision.
- No runtime behavior, provider calls, secret handling, or authz implementation changes.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `llm-provider`: Clarify the accepted configuration sources for production provider approval.

## Impact

- Affected docs/specs: `docs/specs/llm-provider.md`, `openspec/specs/llm-provider/spec.md`.
- Affected runtime code: none.
- Dependencies and external systems: none.
