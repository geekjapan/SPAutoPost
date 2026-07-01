## Context

Issue #81 asks whether the approval gate merged across PR #77, #78, #79, and #80 is a narrow documentation/spec consistency issue or a human authorization decision. The repository evidence shows the implemented behavior is already fixed in `src/spautopost/config.py`: production-class providers require approval, and `production_api` also requires the Azure subsection while `AzureOpenAIProvider` independently validates the nested Azure approval flag.

## Decision

Keep runtime behavior unchanged and clarify only the contract text:

- `llm.production_approved: true` is the common approval flag for `production_api`, `production_flow`, and `generic_api`.
- For `production_api`, `llm.azure.production_approved: true` is also accepted by startup config validation because Azure-specific config has its own nested approval field.
- The nested flag does not remove the `llm.azure` requirement or secret-reference restrictions.
- The text does not grant information-security approval; it describes how a previously obtained approval is represented in config.

## Alternatives

- Require only `llm.azure.production_approved` for `production_api`: clearer for Azure but would be a runtime authz policy change and is outside this narrow consistency fix.
- Require only `llm.production_approved` for all providers: simpler docs but contradicts current implementation and PR #78's Azure-specific provider validation.

## Validation

- Run `openspec validate issue-81-llm-production-approval-gate --strict`.
- Run a focused config test file because the implementation gate is represented there and should remain unchanged.
