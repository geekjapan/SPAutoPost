## Why

Issue #13 prepares the source collection layer for CISA KEV, vendor advisory, and RSS/feed sources before implementing every external adapter. Downstream Issues #11, #12, and #14 need a small common contract that returns source metadata, preserves raw fixture hashes, and normalizes items into the existing Advisory DTO without changing the storage schema.

## What Changes

- Add a `SourceAdapter` Protocol and immutable DTOs for adapter status, query, and fetched source documents.
- Add deterministic fixture adapters for KEV, vendor advisory, and RSS/feed sources.
- Normalize KEV status into Advisory references and tags using the existing `Advisory` shape.
- Add fixture tests for KEV, vendor advisory, RSS/feed, and CVE filtering.
- Update `docs/specs/source-collection.md` with the interface boundary and responsibility split.
- **Non-goals**: live CISA/NVD/MyJVN/vendor network clients, full vendor adapter coverage, crawler implementation, storage schema changes, threat-intelligence platform integration.

## Capabilities

### New Capabilities

- `source-adapter-interface`: fixture-first adapter contract for KEV/vendor/RSS source collection.

### Modified Capabilities

<!-- No existing OpenSpec capability requirements are modified. -->

## Impact

- **Code**: adds `spautopost.source_adapters`.
- **Tests**: adds fixture unit tests.
- **Docs**: updates source collection spec.
- **Runtime / DB**: no storage migration or external calls.
- **Security**: no secrets, credentials, tokens, auth, or publish behavior.
