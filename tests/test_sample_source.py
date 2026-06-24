"""sample source job の単体テスト。"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from spautopost.llm import MockLLMProvider
from spautopost.sample_source import (
    SAMPLE_SOURCE_NAME,
    advisory_from_sample_candidate,
    fetch_sample_source_candidates,
    run_sample_source_job,
)
from spautopost.storage.sqlite_backend import build_sqlite_storage

NOW = datetime(2026, 6, 24, 12, 0, tzinfo=UTC)


def test_sample_candidate_converts_to_source_record_and_advisory() -> None:
    candidate = fetch_sample_source_candidates()[0]

    source_record, advisory = advisory_from_sample_candidate(candidate, now=NOW)

    assert source_record.source_type == "vendor"
    assert source_record.source_name == SAMPLE_SOURCE_NAME
    assert source_record.source_url == candidate.source_url
    assert source_record.raw_hash
    assert advisory.source_record_id == source_record.source_record_id
    assert advisory.title == candidate.title
    assert advisory.references == candidate.references
    assert advisory.tags == candidate.tags


def test_sample_source_job_saves_source_advisory_and_draft(tmp_path: Path) -> None:
    storage = build_sqlite_storage(tmp_path / "sample.sqlite3")
    storage.migrate()

    try:
        results = run_sample_source_job(
            storage,
            MockLLMProvider(prompt_version="v1"),
            now=NOW,
        )
        result = results[0]

        assert storage.source_records.get(result.source_record.source_record_id) == (
            result.source_record
        )
        assert storage.advisories.get(result.advisory.advisory_id) == result.advisory
        saved_draft = storage.draft_posts.get(result.draft_post.draft_id)
        assert saved_draft == result.draft_post
        assert saved_draft is not None
        assert saved_draft.status == "generated"
        assert saved_draft.advisory_id == result.advisory.advisory_id
        assert saved_draft.generated_by_provider == "test_mock"
        assert saved_draft.prompt_version == "v1"
        assert saved_draft.generation_input_hash
        events = storage.audit_events.list()
        event_types = {event.event_type for event in events}
        assert event_types == {"source_fetch", "draft_generate"}
        draft_event = next(event for event in events if event.event_type == "draft_generate")
        assert draft_event.related_ids
        assert draft_event.related_ids["draft_id"] == saved_draft.draft_id
    finally:
        storage.close()


def test_sample_source_job_does_not_overwrite_existing_draft(tmp_path: Path) -> None:
    storage = build_sqlite_storage(tmp_path / "sample.sqlite3")
    storage.migrate()

    try:
        first = run_sample_source_job(storage, MockLLMProvider(prompt_version="v1"), now=NOW)[0]
        reviewed = replace(
            first.draft_post,
            status="reviewed",
            reviewer="admin",
            review_comments=("keep this review",),
            updated_at=datetime(2026, 6, 25, 12, 0, tzinfo=UTC),
        )
        storage.draft_posts.upsert(reviewed)

        second = run_sample_source_job(storage, MockLLMProvider(prompt_version="v1"), now=NOW)[0]

        assert second.draft_post == reviewed
        assert storage.draft_posts.get(reviewed.draft_id) == reviewed
        event_types = [event.event_type for event in storage.audit_events.list()]
        assert event_types.count("source_fetch") == 2
        assert event_types.count("draft_generate") == 1
    finally:
        storage.close()
