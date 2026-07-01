"""Scheduler abstraction: manual/scheduled RunMode.

正本: openspec/changes/issue-21-add-scheduler-external-collector-boundary/

責務: manual run と scheduled run の実行方式を型として区別し、
      JobContext としてジョブ実行コンテキストに付与する。
非責務: cron デーモン・タスクキュー・高可用ジョブ基盤の実装。
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Literal

RunMode = Literal["manual", "scheduled"]

# manual として扱う job 名（job_entrypoint.py の JOB_COMMANDS 参照）。
_MANUAL_JOBS: frozenset[str] = frozenset({"dry-run", "publish-approved"})


@dataclass(frozen=True)
class JobContext:
    """ジョブ実行コンテキスト。RunMode と job 名を保持する。"""

    job_name: str
    run_mode: RunMode


current_job_context: ContextVar[JobContext | None] = ContextVar("current_job_context", default=None)
"""現在のジョブ実行コンテキスト（ContextVar）。

`job_entrypoint.run_job()` が設定する。監査ログや下流処理から RunMode を参照できる。
"""


def build_job_context(job_name: str) -> JobContext:
    """job 名から JobContext を生成する。

    ``dry-run`` と ``publish-approved`` は手動操作を想定するため manual。
    それ以外（collect, generate など）は scheduled として扱う。
    """
    run_mode: RunMode = "manual" if job_name in _MANUAL_JOBS else "scheduled"
    return JobContext(job_name=job_name, run_mode=run_mode)
