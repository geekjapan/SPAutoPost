"""Azure Container Apps Jobs entrypoint wrapper for SPAutoPost.

Container Apps Jobs / scheduled jobs invoke this wrapper with a single job name.
The wrapper maps the job name to a safe SPAutoPost CLI command and runs it
in-process via :func:`spautopost.cli.main`.

Safety policy (M1):

- Hosted jobs run dry-run by default; publishing is always human-gated.
- ``publish-approved`` is a guarded stub: it never publishes and never calls any
  external SharePoint / Graph API. It returns :data:`EXIT_PUBLISH_GATED` so the
  no-op is unmistakable until an approved publish path lands.

Design / spec: openspec/changes/issue-25-add-azure-container-apps-deployment-skeleton/
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from .cli import main as cli_main

EXIT_UNKNOWN_JOB = 2
EXIT_PUBLISH_GATED = 4

PUBLISH_JOB = "publish-approved"

# job name -> spautopost CLI argv. dry-run is forced where the path is safe.
# ponytail: collect and generate resolve to the same sample-source pipeline in
# M1 (the Python core does collect+generate in one pass). Split into distinct
# CLI commands when separate collect/generate paths actually exist.
JOB_COMMANDS: dict[str, list[str]] = {
    "dry-run": ["--dry-run", "validate-config"],
    "collect": ["--dry-run", "run-sample-source-job"],
    "generate": ["--dry-run", "run-sample-source-job"],
}

AVAILABLE_JOBS: tuple[str, ...] = (*JOB_COMMANDS, PUBLISH_JOB)


def resolve_job(job: str) -> list[str]:
    """Return the spautopost CLI argv for a job name.

    Raises:
        KeyError: if the job name is not a known non-publishing job.
    """
    return list(JOB_COMMANDS[job])


def run_job(job: str) -> int:
    """Run a single named job and return its process exit code."""
    if job == PUBLISH_JOB:
        print(
            "publish-approved is human-gated and not implemented in M1; no publish performed.",
            file=sys.stderr,
        )
        return EXIT_PUBLISH_GATED
    try:
        argv = resolve_job(job)
    except KeyError:
        _print_usage(f"unknown job: {job}")
        return EXIT_UNKNOWN_JOB
    return cli_main(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Entrypoint. Expects exactly one positional argument: the job name."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        _print_usage("usage: spautopost-job <job-name>")
        return EXIT_UNKNOWN_JOB
    return run_job(args[0])


def _print_usage(message: str) -> None:
    print(message, file=sys.stderr)
    print(f"available jobs: {', '.join(AVAILABLE_JOBS)}", file=sys.stderr)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
