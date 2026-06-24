"""Container Apps Jobs entrypoint wrapper の単体テスト。"""

from __future__ import annotations

import pytest

from spautopost import job_entrypoint
from spautopost.job_entrypoint import (
    EXIT_PUBLISH_GATED,
    EXIT_UNKNOWN_JOB,
    JOB_COMMANDS,
    main,
)


@pytest.mark.unit
@pytest.mark.parametrize("job", ["dry-run", "collect", "generate"])
def test_known_job_runs_mapped_cli_command(job: str, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange: CLI を差し替えて実際の config 読み込みを起こさず argv を捕捉する。
    captured: dict[str, list[str]] = {}

    def fake_cli(argv: list[str]) -> int:
        captured["argv"] = argv
        return 0

    monkeypatch.setattr(job_entrypoint, "cli_main", fake_cli)

    # Act
    code = main([job])

    # Assert
    assert code == 0
    assert captured["argv"] == JOB_COMMANDS[job]


@pytest.mark.unit
@pytest.mark.parametrize("job", ["collect", "generate"])
def test_collect_and_generate_force_dry_run(job: str) -> None:
    # collect / generate は publish しない sample-source pipeline に解決される。
    assert "--dry-run" in JOB_COMMANDS[job]
    assert "run-sample-source-job" in JOB_COMMANDS[job]


@pytest.mark.unit
def test_publish_approved_never_publishes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Arrange: CLI が呼ばれたら失敗させ、publish 経路に落ちないことを保証する。
    def boom(argv: list[str]) -> int:  # pragma: no cover - 呼ばれてはいけない
        raise AssertionError("publish-approved must not invoke the CLI")

    monkeypatch.setattr(job_entrypoint, "cli_main", boom)

    # Act
    code = main(["publish-approved"])

    # Assert
    assert code == EXIT_PUBLISH_GATED
    assert "human-gated" in capsys.readouterr().err


@pytest.mark.unit
def test_unknown_job_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["does-not-exist"])

    assert code == EXIT_UNKNOWN_JOB
    err = capsys.readouterr().err
    assert "unknown job" in err
    assert "available jobs" in err


@pytest.mark.unit
@pytest.mark.parametrize("argv", [[], ["dry-run", "extra"]])
def test_requires_exactly_one_job_name(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    code = main(argv)

    assert code == EXIT_UNKNOWN_JOB
    assert "usage" in capsys.readouterr().err
