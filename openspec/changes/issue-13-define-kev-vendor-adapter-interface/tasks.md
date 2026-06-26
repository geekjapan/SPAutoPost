## 1. OpenSpec change

- [x] 1.1 Create `source-adapter-interface` capability proposal and spec.
- [x] 1.2 Keep live external API clients out of scope.

## 2. Implementation

- [x] 2.1 Define `SourceAdapter` Protocol and fixture DTOs.
- [x] 2.2 Add KEV fixture normalization.
- [x] 2.3 Add vendor advisory fixture normalization.
- [x] 2.4 Add RSS/feed fixture skeleton normalization.
- [x] 2.5 Add fixture-based unit tests.
- [x] 2.6 Update source collection docs with the responsibility boundary.

## 3. Verification and PR

- [x] 3.1 `pytest tests/test_source_adapters.py`
- [x] 3.2 `ruff check src tests`
- [x] 3.3 `mypy src`
- [x] 3.4 `openspec validate issue-13-define-kev-vendor-adapter-interface --strict`
- [x] 3.5 `openspec validate --changes --strict`
- [x] 3.6 `git diff --check`
