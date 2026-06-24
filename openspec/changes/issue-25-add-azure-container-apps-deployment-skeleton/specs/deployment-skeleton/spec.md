## ADDED Requirements

### Requirement: Container image build premise for the Python core
The system SHALL provide a container image build definition for the Python core that installs the package and uses the SPAutoPost CLI as the container entrypoint, so Azure Container Apps Jobs can invoke CLI commands.

#### Scenario: Core image runs a CLI command
- **WHEN** the core image is built and started with a job name argument
- **THEN** it runs the corresponding SPAutoPost CLI command without requiring a host Python install

### Requirement: Hosted job entrypoint maps job names to safe CLI commands
The system SHALL provide a hosted job entrypoint that maps a single job name (`dry-run`, `collect`, `generate`, `publish-approved`) to a SPAutoPost CLI invocation, and SHALL reject unknown job names with a non-zero exit code.

#### Scenario: Known job maps to a CLI command
- **WHEN** the job entrypoint is invoked with `collect` or `generate`
- **THEN** it runs the corresponding non-publishing CLI command and returns its exit code

#### Scenario: Unknown job is rejected
- **WHEN** the job entrypoint is invoked with an unrecognized job name
- **THEN** it prints the available jobs and returns a non-zero exit code without running any command

### Requirement: Publish-approved job never publishes in M1
The system SHALL treat the `publish-approved` job as a guarded stub that performs no publish and calls no external SharePoint or Graph API, returning a dedicated exit code that marks the no-op.

#### Scenario: Publish-approved is a guarded no-op
- **WHEN** the job entrypoint is invoked with `publish-approved`
- **THEN** it performs no external publish and returns a dedicated exit code indicating the human-gated path is not implemented

### Requirement: Scheduled job command skeletons are defined
The system SHALL provide a reference manifest describing Container Apps Jobs command skeletons for the dry-run, collect, generate, and publish-approved paths, including command, schedule placeholder, and secret reference shape.

#### Scenario: Manifest describes each job path
- **WHEN** an operator reads the jobs reference manifest
- **THEN** each of the four job paths lists its image, entrypoint command, job name argument, and secret references without containing real secret values

### Requirement: Local and hosted configuration are separated
The system SHALL provide separate local and hosted configuration examples, where local uses sqlite/development and hosted uses postgresql/production, and both reference secrets only through `env:` references rather than literal values.

#### Scenario: Hosted config example uses env references for secrets
- **WHEN** the hosted configuration example is inspected
- **THEN** every secret (database URL, tenant, SharePoint target identifiers) is expressed as an `env:` reference and no literal secret value is present

### Requirement: Hosted run is documented
The system SHALL document the difference between local execution and Azure-intended hosted execution, including required environment variables and secret references.

#### Scenario: Documentation explains local vs hosted run
- **WHEN** a reader follows the README and deploy documentation
- **THEN** they can distinguish local CLI execution from the Azure Container Apps Jobs execution and know which environment variables and secret references the hosted run requires
