# Tasks

## 1. Adapter implementation
- [x] 1.1 Add `spautopost.nvd_adapter` with injectable transport, response/rate-limit DTOs, and a default stdlib `urllib` transport against the fixed NVD HTTPS base URL.
- [x] 1.2 Build request params for CVE-ID fetch (`cveIds`, capped at 100) and date-range fetch (`pubStartDate`/`pubEndDate`, `lastModStartDate`/`lastModEndDate`, 120-day max validation).
- [x] 1.3 Implement pagination over `startIndex`/`resultsPerPage`/`totalResults`/`vulnerabilities`.
- [x] 1.4 Implement rate-limit policy: minimum request interval + `Retry-After`-aware bounded retry on 429/503 via an injectable sleeper.
- [x] 1.5 Normalize NVD CVE JSON into `Advisory` (summary, CVSS v3.1>v3.0>v2 score/vector/severity, CPE vendor/product tags, references, KEV tag/reference) and populate `SourceRecord.source_url`/`retrieved_at`/`raw_hash`.
- [x] 1.6 Accept an optional API key via constructor injection sent as the `apiKey` header; never log/store it.

## 2. Tests
- [x] 2.1 CVE-ID fetch + normalization and >100 CVE-ID rejection.
- [x] 2.2 Date-range fetch and >120-day rejection.
- [x] 2.3 Pagination across multiple pages.
- [x] 2.4 Rate-limit interval + Retry-After retry and bounded-retry failure.
- [x] 2.5 CVSS/CPE/references/KEV normalization and missing-metrics fallback.

## 3. Verification
- [x] 3.1 `pytest` (targeted + full), `ruff check`/`ruff format --check`, `mypy src`.
- [x] 3.2 `openspec validate issue-11-implement-nvd-adapter --strict` and `openspec validate --changes --strict`.
