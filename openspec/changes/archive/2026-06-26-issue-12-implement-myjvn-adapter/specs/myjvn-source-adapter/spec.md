## ADDED Requirements

### Requirement: MyJVN adapter fetches vulnerability overview XML

MyJVN adapter SHALL fetch `getVulnOverviewList` HND XML through an injectable transport and return one `SourceDocument` per overview item without requiring credentials.

#### Scenario: Overview item is fetched and normalized
- **WHEN** the adapter fetches overview XML through a fixture transport
- **THEN** it returns a source document whose `SourceRecord` has `source_type` `myjvn`, a JVN iPedia `source_url`, `retrieved_at`, and `raw_hash`
- **THEN** normalization yields an `Advisory` carrying the JVN ID, CVE ID, Japanese title, Japanese summary, references, published time, and updated time

#### Scenario: MyJVN status error is rejected
- **WHEN** the XML contains a MyJVN `Status` node with `retCd="1"`
- **THEN** the adapter raises an error instead of returning partial documents

### Requirement: MyJVN adapter fetches vulnerability detail XML

MyJVN adapter SHALL fetch `getVulnDetailInfo` HND XML by one or more JVN IDs and MUST reject an empty detail ID list before calling transport.

#### Scenario: Detail item preserves Japanese mitigation
- **WHEN** the adapter fetches detail XML for a JVN ID through a fixture transport
- **THEN** normalization yields an `Advisory` whose summary contains the Japanese overview and mitigation text from `Solution`

#### Scenario: Empty detail request is rejected
- **WHEN** detail fetch is requested with no JVN IDs
- **THEN** the adapter raises an error without calling transport

### Requirement: MyJVN adapter uses stdlib transport only

MyJVN adapter MUST use stdlib `urllib` for the default real HTTP transport and MUST NOT add a new runtime dependency.

#### Scenario: Default transport enforces HTTPS
- **WHEN** the default transport is called with a non-HTTPS URL
- **THEN** it raises an adapter error before any request is made

### Requirement: MyJVN source usage requirements are documented

Source collection docs MUST state that operators need to follow MyJVN API terms of use and display that information was provided by MyJVN API when showing derived information.

#### Scenario: Docs include terms and source-display guidance
- **WHEN** `docs/specs/source-collection.md` is reviewed
- **THEN** the MyJVN section states the terms-of-use check and source attribution requirement
