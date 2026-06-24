## 1. OpenSpec

- [x] 1.1 Create proposal, design, and deployment-skeleton spec for Issue #25

## 2. Container build premise

- [x] 2.1 Add `deploy/Dockerfile.core` (Python core image) with CLI job entrypoint and migration SQL
- [x] 2.2 Add `deploy/Dockerfile.admin` and `.dockerignore` for the Admin API skeleton

## 3. Job entrypoint and command skeletons

- [x] 3.1 Add `spautopost-job` wrapper mapping job names to safe CLI commands
- [x] 3.2 Stub `publish-approved` as a guarded no-op (never publishes)
- [x] 3.3 Add `deploy/jobs.example.yaml` Container Apps Jobs command skeletons

## 4. Local vs hosted config separation

- [x] 4.1 Add `deploy/config.hosted.example.yml` (production / postgresql / env refs)
- [x] 4.2 Add `deploy/hosted.env.example` env / secret reference examples (no real values)
- [x] 4.3 Resolve hosted `env:` database URL before constructing PostgreSQL storage

## 5. Docs

- [x] 5.1 Document local run vs Azure-intended run in README and `deploy/README.md`

## 6. Verification

- [x] 6.1 Add tests for the job entrypoint mapping and publish-approved guard
- [x] 6.2 Run OpenSpec validation and Python checks (ruff / mypy / pytest)
