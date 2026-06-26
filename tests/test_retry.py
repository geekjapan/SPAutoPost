"""retry/backoff ユーティリティのテスト。"""

from __future__ import annotations

import pytest

from spautopost.retry import RetryConfig, with_retry


@pytest.mark.unit
def test_successful_call_returns_value() -> None:
    result = with_retry(lambda: 42)
    assert result == 42


@pytest.mark.unit
def test_retry_after_transient_failure() -> None:
    calls = [0]
    slept: list[float] = []

    def flaky() -> str:
        calls[0] += 1
        if calls[0] < 3:
            raise RuntimeError("transient")
        return "ok"

    config = RetryConfig(max_attempts=3, base_delay_seconds=0.0, sleep_fn=slept.append)
    result = with_retry(flaky, config)
    assert result == "ok"
    assert calls[0] == 3
    assert len(slept) == 2  # 2 delays before 3rd attempt


@pytest.mark.unit
def test_all_attempts_fail_raises_last_exception() -> None:
    calls = [0]

    def always_fails() -> str:
        calls[0] += 1
        raise ValueError(f"fail #{calls[0]}")

    config = RetryConfig(max_attempts=3, base_delay_seconds=0.0, sleep_fn=lambda _: None)
    with pytest.raises(ValueError, match="fail #3"):
        with_retry(always_fails, config)
    assert calls[0] == 3


@pytest.mark.unit
def test_max_attempts_one_does_not_retry() -> None:
    calls = [0]

    def fail_once() -> str:
        calls[0] += 1
        raise RuntimeError("fail")

    config = RetryConfig(max_attempts=1, base_delay_seconds=0.0, sleep_fn=lambda _: None)
    with pytest.raises(RuntimeError):
        with_retry(fail_once, config)
    assert calls[0] == 1


@pytest.mark.unit
def test_backoff_delays_grow_exponentially() -> None:
    slept: list[float] = []
    calls = [0]

    def fail_3() -> None:
        calls[0] += 1
        if calls[0] <= 3:
            raise RuntimeError()

    config = RetryConfig(
        max_attempts=4,
        base_delay_seconds=1.0,
        max_delay_seconds=10.0,
        backoff_factor=2.0,
        sleep_fn=slept.append,
    )
    with_retry(fail_3, config)
    assert slept == [1.0, 2.0, 4.0]


@pytest.mark.unit
def test_delay_capped_at_max() -> None:
    slept: list[float] = []
    calls = [0]

    def fail_3() -> None:
        calls[0] += 1
        if calls[0] <= 3:
            raise RuntimeError()

    config = RetryConfig(
        max_attempts=4,
        base_delay_seconds=5.0,
        max_delay_seconds=7.0,
        backoff_factor=2.0,
        sleep_fn=slept.append,
    )
    with_retry(fail_3, config)
    assert all(d <= 7.0 for d in slept)


@pytest.mark.unit
def test_default_config_is_valid() -> None:
    config = RetryConfig()
    assert config.max_attempts >= 1
    assert config.base_delay_seconds >= 0
    assert config.max_delay_seconds >= config.base_delay_seconds


@pytest.mark.unit
def test_invalid_max_attempts_raises() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        RetryConfig(max_attempts=0)


@pytest.mark.unit
def test_invalid_base_delay_raises() -> None:
    with pytest.raises(ValueError, match="base_delay"):
        RetryConfig(base_delay_seconds=-1.0)


@pytest.mark.unit
def test_invalid_max_delay_raises() -> None:
    with pytest.raises(ValueError, match="max_delay"):
        RetryConfig(base_delay_seconds=10.0, max_delay_seconds=5.0)


@pytest.mark.unit
def test_invalid_backoff_factor_raises() -> None:
    with pytest.raises(ValueError, match="backoff_factor"):
        RetryConfig(backoff_factor=0.0)
