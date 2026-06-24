## ADDED Requirements

### Requirement: Advisories sharing an identifier are merged

The system SHALL merge `Advisory` records that share a CVE ID, JVN ID, or vendor advisory ID into a single Advisory, resolving identity transitively so that records linked through different identifier types are grouped together. Advisories without any identifier SHALL remain separate.

#### Scenario: Same CVE from multiple sources is merged
- **WHEN** a KEV Advisory and a vendor advisory share one CVE ID
- **THEN** `merge_advisories` returns a single Advisory that unions the CVE IDs, vendor advisory IDs, references, and tags, keeps the maximum severity and CVSS score, and uses the earliest published date

#### Scenario: Identity is resolved transitively
- **WHEN** advisory A shares a CVE with B, and B shares a JVN ID with C
- **THEN** A, B, and C are merged into one Advisory

#### Scenario: Identifier-less advisories stay separate
- **WHEN** two advisories have no CVE, JVN, or vendor advisory ID
- **THEN** they are not merged and remain distinct candidates for human review

### Requirement: Priority score and urgency are computed

The system SHALL compute an additive priority score from severity, KEV listing, exploit status, patch availability, internal relevance, internet-facing exposure, and source confidence, and SHALL map the score to an urgency label using documented thresholds. KEV listing SHALL be detected from an explicit signal or from KEV tags on the Advisory.

#### Scenario: Documented weights are summed
- **WHEN** a critical Advisory is KEV listed with confirmed exploit, available patch, confirmed internal relevance, and internet-facing exposure
- **THEN** `priority_score` returns the sum of the documented weights

#### Scenario: Score maps to urgency
- **WHEN** a priority score is at least 80
- **THEN** `urgency_for_score` returns `emergency`, and lower bands return `high`, `normal`, or `low` per the documented thresholds

### Requirement: CVSS score maps to severity

The system SHALL map a CVSS base score to a severity label using the documented ranges, and SHALL treat a missing score as `unknown`.

#### Scenario: CVSS is mapped during merge
- **WHEN** merged advisories have `unknown` severity but a CVSS score of 9.3
- **THEN** the merged Advisory severity is `critical`

### Requirement: Duplicate-post guard key is generated

The system SHALL generate a stable duplicate-post key from the deduplicated sorted CVE / JVN / vendor advisory IDs, the normalized title, and the target audience, so that the same content yields the same key and different audiences yield different keys. Identifier-less advisories SHALL include their advisory ID in the key material to avoid collisions between distinct advisories with generic titles.

#### Scenario: Same identity yields same key
- **WHEN** two advisories share the same CVE ID and an equivalent title differing only by case and whitespace
- **THEN** `duplicate_post_key` returns the same key for both

#### Scenario: Audience changes the key
- **WHEN** the same Advisory is keyed for `general_users` and for `administrators`
- **THEN** the two duplicate-post keys differ

#### Scenario: Identifier-less advisories avoid generic-title collisions
- **WHEN** two advisories have no CVE, JVN, or vendor advisory ID and share the same normalized title
- **THEN** `duplicate_post_key` returns different keys by including each advisory ID

### Requirement: Triage is deterministic and local

Triage SHALL be deterministic and SHALL NOT perform network calls, ML inference, asset-inventory matching, automatic publish decisions, or storage schema changes.

#### Scenario: Triage returns combined result
- **WHEN** `triage` is called for an Advisory with signals and an audience
- **THEN** it returns the priority score, urgency label, and duplicate-post key without external I/O
