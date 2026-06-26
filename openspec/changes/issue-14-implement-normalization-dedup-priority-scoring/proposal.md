## Why

Issue #14 (Milestone M2) requires merging vulnerability information collected from multiple sources (NVD, MyJVN, KEV, vendor advisories, RSS) into post candidates and prioritizing them. The same vulnerability arrives from several sources, so the system needs deterministic deduplication, severity/priority scoring, an urgency label, and a stable key that prevents duplicate posts. The source-adapter layer (Issue #13) already normalizes raw items into the `Advisory` DTO; this change adds the merge/score/triage step on top of it without touching the storage schema.

## What Changes

- Add `spautopost.triage` with deterministic, local-only normalization triage:
  - `merge_advisories`: dedup Advisory records that share a CVE / JVN / vendor advisory ID (transitive union-find), unioning identifiers/references/tags and keeping the maximum severity and CVSS.
  - `priority_score` / `urgency_for_score`: additive scoring and urgency label per the documented rule.
  - `severity_from_cvss`: CVSS base score → severity label.
  - `duplicate_post_key`: stable full-digest key from deduplicated sorted identifiers + normalized title + audience, with advisory ID fallback for identifier-less records, to guard against re-posting.
  - `triage`: convenience wrapper returning score, urgency, and duplicate key for one Advisory.
- Add fixture/test-data driven unit tests for merge, scoring, urgency thresholds, CVSS mapping, and duplicate key stability.
- Document the scoring rule and duplicate-post guard in `docs/specs/normalization-and-triage.md` (constants made explicit and reconciled with code).
- **Non-goals**: ML-based prioritization, full internal asset-inventory matching, automatic publish decisions, storage schema changes, live network clients.

## Capabilities

### New Capabilities

- `normalization-triage`: deterministic dedup, priority scoring, urgency labeling, and duplicate-post key generation over the existing `Advisory` DTO.

### Modified Capabilities

<!-- No existing OpenSpec capability requirements are modified. -->

## Impact

- **Code**: adds `spautopost.triage` (pure computation; no I/O).
- **Tests**: adds `tests/test_triage.py`.
- **Docs**: updates `docs/specs/normalization-and-triage.md` with explicit scoring constants.
- **Runtime / DB**: no storage migration, no external calls, no DTO changes.
- **Security**: no secrets, credentials, tokens, auth, or publish behavior; duplicate key uses SHA-256 over non-secret identifiers.
