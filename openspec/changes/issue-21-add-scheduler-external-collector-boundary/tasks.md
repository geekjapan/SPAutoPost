## 1. OpenSpec

- [x] 1.1 Create proposal, design, specs, and tasks for Issue #21

## 2. Implementation

- [ ] 2.1 Add `RunMode` / `JobContext` to `scheduler.py` and wire into `job_entrypoint.py`
- [ ] 2.2 Add `CollectionCheckpoint` and `CollectionCheckpointStore` to `collection_checkpoint.py`
- [ ] 2.3 Add retry/backoff utility to `retry.py`
- [ ] 2.4 Add `ExternalCollectorImportPort` Protocol and `FileExternalCollectorImporter` to `external_collector_import.py`
- [ ] 2.5 Add `import-external` CLI command to `cli.py`
- [ ] 2.6 Update `docs/specs/external-collector-boundary.md` to align import schema with implementation

## 3. Tests

- [ ] 3.1 `tests/test_scheduler.py` — RunMode / JobContext
- [ ] 3.2 `tests/test_collection_checkpoint.py` — save/load/missing
- [ ] 3.3 `tests/test_retry.py` — success/failure/max-attempts
- [ ] 3.4 `tests/test_external_collector_import.py` — schema validation, advisory conversion, reject counts

## 4. Verification

- [ ] 4.1 `ruff check . && ruff format --check src tests`
- [ ] 4.2 `mypy src`
- [ ] 4.3 `pytest --cov=spautopost --cov-report=term-missing` (coverage >= 80%)
- [ ] 4.4 `openspec validate issue-21-add-scheduler-external-collector-boundary --strict`
