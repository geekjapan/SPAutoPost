## 1. OpenSpec change

- [x] 1.1 Create `normalization-triage` capability proposal and spec.
- [x] 1.2 Keep ML prioritization, asset-inventory matching, and auto-publish out of scope.

## 2. Implementation

- [x] 2.1 Add `merge_advisories` dedup by shared CVE / JVN / vendor advisory ID (transitive).
- [x] 2.2 Add `priority_score` and `urgency_for_score` additive scoring.
- [x] 2.3 Add `severity_from_cvss` mapping.
- [x] 2.4 Add `duplicate_post_key` stable re-post guard key.
- [x] 2.5 Add `triage` wrapper returning score, urgency, and duplicate key.
- [x] 2.6 Add fixture/test-data driven unit tests.
- [x] 2.7 Document the scoring rule and duplicate-post guard with explicit constants.

## 3. Verification and PR

- [x] 3.1 `pytest tests/spautopost/test_triage.py`
- [x] 3.2 `ruff check src tests`
- [x] 3.3 `mypy src`
- [x] 3.4 `openspec validate issue-14-implement-normalization-dedup-priority-scoring --strict`
- [x] 3.5 `openspec validate --changes --strict`
- [x] 3.6 `git diff --check`
