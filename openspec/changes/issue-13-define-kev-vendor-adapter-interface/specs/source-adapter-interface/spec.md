## ADDED Requirements

### Requirement: Source adapter interface is defined

The system SHALL define a `SourceAdapter` interface that validates configuration, fetches source documents for a query, and normalizes each source document into Advisory records.

#### Scenario: Fixture adapter is used by downstream collectors
- **WHEN** an adapter is created for KEV, vendor advisory, or RSS/feed fixtures
- **THEN** callers can validate configuration, fetch deterministic source documents, and normalize them without external network access

### Requirement: KEV status is reflected on Advisory

KEV fixture normalization SHALL reflect known-exploited status on the resulting Advisory using existing Advisory fields.

#### Scenario: KEV fixture is normalized
- **WHEN** a KEV item with a CVE ID is normalized
- **THEN** the Advisory includes the CVE ID, a KEV reference, and tags including `kev` and `known-exploited`

### Requirement: Vendor advisory fixture normalizes into Advisory

Vendor advisory fixture normalization SHALL preserve vendor advisory identifiers, source URL, CVE IDs, severity, and tags on Advisory.

#### Scenario: Vendor advisory fixture is normalized
- **WHEN** a vendor advisory fixture item is normalized
- **THEN** the Advisory has a stable vendor advisory ID, a vendor reference, CVE IDs, and source-linked metadata

### Requirement: RSS/feed adapter skeleton is fixture-backed

RSS/feed fixture normalization SHALL convert feed item title, URL, summary, dates, and CVE IDs into Advisory without implementing a live feed crawler.

#### Scenario: Feed fixture item is normalized
- **WHEN** a feed item fixture is normalized
- **THEN** the Advisory has an RSS source type, feed reference, and deterministic advisory ID

### Requirement: Source collection docs describe responsibility boundary

`docs/specs/source-collection.md` SHALL document the fixture-first SourceAdapter boundary and state that live network clients are owned by later source-specific Issues.

#### Scenario: New source is added later
- **WHEN** an implementation agent adds NVD, MyJVN, KEV, or vendor-specific live adapters
- **THEN** the agent can follow the documented boundary and avoid mixing crawler, parser, normalization, and storage responsibilities
