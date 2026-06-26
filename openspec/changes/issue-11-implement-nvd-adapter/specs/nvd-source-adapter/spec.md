## ADDED Requirements

### Requirement: NVD adapter fetches CVEs by ID

The NVD adapter SHALL fetch CVE records by one or more CVE IDs using the NVD CVE API 2.0 `cveIds` parameter and an injectable transport, returning one source document per CVE.

#### Scenario: Single CVE ID is fetched and normalized
- **WHEN** the adapter fetches a query containing a CVE ID through a fixture transport
- **THEN** it returns a source document whose `SourceRecord` has `source_type` `nvd`, a per-CVE NVD detail `source_url`, and `retrieved_at`, and normalization yields an Advisory carrying that CVE ID

#### Scenario: More than 100 CVE IDs are rejected
- **WHEN** a fetch is requested with more than 100 CVE IDs
- **THEN** the adapter raises an error without calling the transport

### Requirement: NVD adapter fetches by date range

The NVD adapter SHALL support published and last-modified date-range fetch using `pubStartDate`/`pubEndDate` and `lastModStartDate`/`lastModEndDate`, and SHALL reject ranges exceeding the NVD 120-day maximum.

#### Scenario: Last-modified delta is fetched
- **WHEN** the adapter fetches with a modified-from/modified-to range within 120 days
- **THEN** it sends the `lastModStartDate`/`lastModEndDate` parameters and returns the matching CVEs

#### Scenario: Over-120-day range is rejected
- **WHEN** a date range spans more than 120 consecutive days
- **THEN** the adapter raises an error without calling the transport

### Requirement: NVD adapter paginates results

The NVD adapter SHALL page through results using `startIndex`, `resultsPerPage`, and `totalResults`, accumulating every item in `vulnerabilities` until all results are retrieved.

#### Scenario: Results span multiple pages
- **WHEN** `totalResults` exceeds `resultsPerPage`
- **THEN** the adapter issues successive requests with increasing `startIndex` and returns source documents for every CVE across all pages

### Requirement: NVD adapter respects rate limits

The NVD adapter SHALL apply an explicit, configurable minimum interval between requests and SHALL honor a `Retry-After` header on HTTP 429/503 responses, using an injectable sleeper so the behavior is testable without real delay.

#### Scenario: Retry-After is honored
- **WHEN** the transport returns HTTP 429 with a `Retry-After` header and then a success
- **THEN** the adapter waits the indicated interval through the injected sleeper and completes the fetch

#### Scenario: Retries are bounded
- **WHEN** the transport keeps returning a retryable status beyond the retry limit
- **THEN** the adapter raises an error instead of retrying forever

### Requirement: NVD adapter normalizes CVSS, CPE, references, and KEV

NVD normalization SHALL populate Advisory CVSS version/score/vector and severity (preferring CVSS v3.1, then v3.0, then v2), extract CPE vendor/product hints as tags, preserve references, and reflect CISA KEV status when present.

#### Scenario: CVSS and KEV are normalized
- **WHEN** a CVE item with CVSS v3.1 metrics, CPE configurations, references, and a `cisaExploitAdd` date is normalized
- **THEN** the Advisory has the v3.1 score/vector/severity, `vendor:`/`product:` tags from CPE, the references, and tags including `kev` and `known-exploited`

#### Scenario: Missing metrics fall back to unknown severity
- **WHEN** a CVE item has no CVSS metrics
- **THEN** the Advisory severity is `unknown` and CVSS fields are unset
