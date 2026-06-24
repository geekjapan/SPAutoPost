## Why

Issue #11 (Milestone M2) makes NVD the first live vulnerability source. The fixture-first `SourceAdapter` contract from Issue #13 is in place, but there is no adapter that fetches CVE data from the NVD CVE API 2.0 and normalizes it into the existing `Advisory` DTO. NVD is the primary CVE source, so SPAutoPost needs a deterministic, testable NVD adapter that handles CVE-ID and date-range fetch, pagination, and rate limits without storing secrets or calling live NVD in tests.

## What Changes

- Add `spautopost.nvd_adapter` with an injectable transport so unit/fixture tests never call live NVD.
- Support CVE-ID fetch (`cveIds`, comma-separated, capped at 100 per NVD) and published/last-modified date-range fetch (`pubStartDate`/`pubEndDate`, `lastModStartDate`/`lastModEndDate`, 120-day max per NVD).
- Handle pagination via `startIndex`/`resultsPerPage`/`totalResults`/`vulnerabilities`.
- Apply an explicit, testable rate-limit policy: a configurable minimum request interval plus `Retry-After`-aware retry on HTTP 429/503, with an injectable sleeper so tests add no real delay.
- Normalize NVD CVE JSON into `Advisory`: description summary, CVSS (v3.1 > v3.0 > v2) version/score/vector/severity, CPE vendor/product hints as tags, references, and KEV status (`cisaExploitAdd`) preserved as a tag and reference.
- Populate `SourceRecord.source_url` (per-CVE NVD detail URL) and `retrieved_at`, plus `raw_hash`/`parser_version`.
- Accept an optional API key via constructor injection (sent as the `apiKey` header), never logged, stored, or committed; tests stay secret-free.
- Add unit/fixture tests covering CVE-ID fetch, date-range fetch, pagination, rate-limit/Retry-After, CVSS/CPE/references/KEV normalization, and date-range validation.
- **Non-goals**: bulk sync of all CVEs, full internal asset matching, non-NVD source integration, wiring the adapter into a scheduled job/CLI.

## Capabilities

### New Capabilities

- `nvd-source-adapter`: live NVD CVE API 2.0 adapter with injectable transport, pagination, rate limiting, and Advisory normalization.

### Modified Capabilities

<!-- No existing OpenSpec capability requirements are modified. -->

## Impact

- **Code**: adds `spautopost.nvd_adapter` (conforms to the existing `SourceAdapter` Protocol).
- **Tests**: adds fixture-backed unit tests; no live network access.
- **Docs**: none required beyond the spec delta (source-collection boundary already documents live-adapter ownership).
- **Runtime / DB**: no storage migration; default real transport uses stdlib `urllib` against the fixed NVD HTTPS base URL.
- **Security**: optional API key is injected and sent only as a request header; never logged, stored, or committed. No auth/publish behavior is added.
