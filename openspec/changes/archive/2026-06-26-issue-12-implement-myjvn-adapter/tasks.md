# Tasks

## 1. OpenSpec
- [x] 1.1 Create proposal, design, spec delta, and tasks for Issue #12.
- [x] 1.2 Validate `issue-12-implement-myjvn-adapter` with `--strict`.

## 2. Tests
- [x] 2.1 Add fixture tests for overview fetch + normalization.
- [x] 2.2 Add fixture tests for detail fetch + mitigation preservation.
- [x] 2.3 Add error tests for MyJVN status error, empty detail request, and non-HTTPS default transport.

## 3. Adapter implementation
- [x] 3.1 Add `spautopost.myjvn_adapter` with injectable transport and default stdlib `urllib` transport.
- [x] 3.2 Implement `getVulnOverviewList` request building, XML parsing, SourceRecord creation, and pagination.
- [x] 3.3 Implement `getVulnDetailInfo` request building, XML parsing, and JVN ID validation.
- [x] 3.4 Normalize overview/detail XML into `Advisory` with JVN ID, CVE ID, Japanese title/summary/mitigation, references, CVSS, and date fields.

## 4. Docs
- [x] 4.1 Document MyJVN API terms-of-use and source attribution handling in `docs/specs/source-collection.md`.

## 5. Verification and closeout
- [x] 5.1 Run targeted tests and full relevant checks.
- [x] 5.2 Archive/sync the OpenSpec change.
- [x] 5.3 Commit, push, and create a PR against `main`.
