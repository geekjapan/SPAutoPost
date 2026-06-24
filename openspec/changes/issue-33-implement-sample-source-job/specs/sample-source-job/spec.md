## ADDED Requirements

### Requirement: Sample source retrieves posting candidates
The system SHALL provide a sample source job that retrieves at least one deterministic posting candidate without calling external APIs or crawlers.

#### Scenario: Retrieve deterministic candidate
- **WHEN** the sample source job fetches candidates
- **THEN** it returns source metadata and advisory content suitable for M1 draft generation

### Requirement: Sample source converts candidates to Advisory
The system SHALL convert each sample source candidate into the existing `Advisory` model while preserving source metadata linkage through `source_record_id`.

#### Scenario: Convert to advisory
- **WHEN** a sample source candidate is normalized
- **THEN** the resulting `Advisory` contains title, summary, references, severity, tags, and the related `source_record_id`

### Requirement: Sample source persists source, advisory, and draft
The system SHALL save `SourceRecord`, `Advisory`, and generated `DraftPost` through the existing `StoragePort`.

#### Scenario: Save pipeline output
- **WHEN** the sample source job runs with a storage port and draft provider
- **THEN** the source record, advisory, and generated draft post are persisted without storing secrets

### Requirement: Sample source hands off to DraftPost generation
The system SHALL pass the converted `Advisory` to the existing DraftPost generation path and store the generated draft with provider and prompt metadata.

#### Scenario: Draft generation handoff
- **WHEN** the sample source job generates a draft
- **THEN** the draft references the advisory, includes generation input hash, and has status `generated`

### Requirement: Scheduled job skeleton can call sample source
The system SHALL expose a scheduled-job-compatible entrypoint that invokes the sample source pipeline without publishing to SharePoint.

#### Scenario: Job skeleton invocation
- **WHEN** the scheduled job skeleton is invoked
- **THEN** it runs the sample source pipeline and reports generated draft identifiers without external publish or account operations
