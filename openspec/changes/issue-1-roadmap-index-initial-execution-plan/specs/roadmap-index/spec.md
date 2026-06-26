## ADDED Requirements

### Requirement: Roadmap index records milestone setup evidence

`docs/roadmap.md` SHALL record that GitHub milestones M0 through M6 exist for SPAutoPost roadmap tracking.

#### Scenario: Agent checks roadmap setup
- **WHEN** an implementation agent opens `docs/roadmap.md`
- **THEN** the agent can see that M0 through M6 are active GitHub milestones rather than only recommendations

### Requirement: Roadmap index records issue allocation evidence

`docs/roadmap.md` SHALL record that GitHub Issues for M0 through M6 are assigned to their corresponding milestones.

#### Scenario: Agent checks issue allocation
- **WHEN** an implementation agent needs to verify Issue #1 completion criteria
- **THEN** the roadmap provides a snapshot showing each milestone has assigned Issues

### Requirement: Roadmap index links the initial implementation order

`docs/roadmap.md` SHALL link the agreed initial implementation order source.

#### Scenario: Agent needs implementation order
- **WHEN** an implementation agent asks what order to follow after M0
- **THEN** the roadmap points to the accepted M1 implementation-order decision record and the milestone sequence

### Requirement: Roadmap index links OpenSpec-first agent rules

`docs/roadmap.md` SHALL link the documents that define the OpenSpec-first rule for implementation agents.

#### Scenario: Agent needs the OpenSpec rule
- **WHEN** an implementation agent starts from the roadmap parent issue
- **THEN** the roadmap points to `AGENTS.md`, `CLAUDE.md`, `docs/openspec-workflow.md`, and `docs/runbooks/multi-agent-orchestration.md`
