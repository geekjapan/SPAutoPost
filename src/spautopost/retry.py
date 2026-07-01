"""失敗時の指数バックオフ付き retry ユーティリティ。

正本: openspec/changes/issue-21-add-scheduler-external-collector-boundary/

責務: callable を最大 max_attempts 回再試行し、指数バックオフで間隔を伸ばす。
非責務: Retry-After ヘッダ解析・サーキットブレーカー・分散協調（後続 Issue）。
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

# 合理的な上限（外部 API が数分停止してもブロックしない）。
_MAX_REASONABLE_DELAY = 3600.0


@dataclass(frozen=True)
class RetryConfig:
    """指数バックオフの設定。"""

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_factor: float = 2.0
    # テスト用: sleep を差し替えられるようにする。
    sleep_fn: Callable[[float], None] = field(default=time.sleep, compare=False)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must be >= 0")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds must be >= base_delay_seconds")
        if self.backoff_factor <= 0:
            raise ValueError("backoff_factor must be > 0")


def with_retry[T](fn: Callable[[], T], config: RetryConfig | None = None) -> T:
    """callable を失敗時に指数バックオフで再試行する。

    全試行が失敗した場合は最後の例外を再発生させる。
    """
    cfg = config or RetryConfig()
    delay = cfg.base_delay_seconds

    for attempt in range(cfg.max_attempts):
        try:
            return fn()
        except Exception:
            if attempt < cfg.max_attempts - 1:
                cfg.sleep_fn(delay)
                delay = min(delay * cfg.backoff_factor, cfg.max_delay_seconds)
            else:
                raise

    raise AssertionError("unreachable")
