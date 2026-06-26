"""RunMode / JobContext のテスト。"""

from __future__ import annotations

import pytest

from spautopost.scheduler import RunMode, build_job_context


@pytest.mark.unit
@pytest.mark.parametrize("job", ["dry-run", "publish-approved"])
def test_manual_jobs_have_manual_run_mode(job: str) -> None:
    ctx = build_job_context(job)
    assert ctx.run_mode == "manual"
    assert ctx.job_name == job


@pytest.mark.unit
@pytest.mark.parametrize("job", ["collect", "generate"])
def test_scheduled_jobs_have_scheduled_run_mode(job: str) -> None:
    ctx = build_job_context(job)
    assert ctx.run_mode == "scheduled"
    assert ctx.job_name == job


@pytest.mark.unit
def test_unknown_job_defaults_to_scheduled() -> None:
    ctx = build_job_context("some-new-job")
    assert ctx.run_mode == "scheduled"


@pytest.mark.unit
def test_job_context_is_frozen() -> None:
    ctx = build_job_context("collect")
    with pytest.raises(AttributeError):
        ctx.run_mode = "manual"  # type: ignore[misc]


@pytest.mark.unit
def test_run_mode_values() -> None:
    manual: RunMode = "manual"
    scheduled: RunMode = "scheduled"
    assert manual != scheduled
