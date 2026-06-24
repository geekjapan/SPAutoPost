"""Azure Container Apps job entrypoint wrapper tests."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts" / "aca-job-entrypoint.sh"


def _fake_spautopost(tmp_path: Path) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    args_file = tmp_path / "args.txt"
    executable = bin_dir / "spautopost"
    executable.write_text(
        '#!/usr/bin/env sh\nprintf "%s\\n" "$@" > "$SPAUTOPOST_ARGS_FILE"\n',
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return bin_dir, args_file


def _run_entrypoint(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    bin_dir, args_file = _fake_spautopost(tmp_path)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "SPAUTOPOST_ARGS_FILE": str(args_file),
    }
    return subprocess.run(  # noqa: S603 - test executes repo-owned wrapper with controlled args
        [str(ENTRYPOINT), *args],
        check=False,
        env=env,
        text=True,
        capture_output=True,
    )


def test_entrypoint_dispatches_generate_job(tmp_path: Path) -> None:
    result = _run_entrypoint(tmp_path, "generate", "--env", "production")

    assert result.returncode == 0
    assert (tmp_path / "args.txt").read_text(encoding="utf-8").splitlines() == [
        "--env",
        "production",
        "generate-drafts",
    ]


def test_entrypoint_dispatches_dry_run_job(tmp_path: Path) -> None:
    result = _run_entrypoint(tmp_path, "dry-run", "--env", "production")

    assert result.returncode == 0
    assert (tmp_path / "args.txt").read_text(encoding="utf-8").splitlines() == [
        "--env",
        "production",
        "--dry-run",
        "dry-run-job",
    ]


def test_entrypoint_rejects_unknown_job(tmp_path: Path) -> None:
    result = _run_entrypoint(tmp_path, "unknown-job")

    assert result.returncode == 64
    assert "unknown SPAutoPost ACA job" in result.stderr
    assert not (tmp_path / "args.txt").exists()
