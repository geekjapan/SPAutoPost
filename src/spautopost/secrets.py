"""Secret 参照（``env:NAME``）の解決と秘匿。

漏洩面を一点に閉じ込めるため、Secret 参照の判定・列挙・redaction を本モジュールに集約する。
実際の Secret 値は本スケルトンでは保持せず、起動時に存在のみを検査する。
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

SECRET_PREFIX = "env:"  # noqa: S105  # 接頭辞であって Secret 値ではない
REDACTED = "***"


def is_secret_ref(value: Any) -> bool:
    """値が ``env:NAME`` 形式の Secret 参照かどうかを返す。"""
    return isinstance(value, str) and value.startswith(SECRET_PREFIX)


def secret_env_name(ref: str) -> str:
    """``env:NAME`` 参照から環境変数名 ``NAME`` を取り出す。"""
    return ref[len(SECRET_PREFIX) :]


def iter_secret_refs(
    data: Any, path: tuple[str, ...] = ()
) -> Iterator[tuple[tuple[str, ...], str]]:
    """設定ツリーを走査し、(パス, 環境変数名) を列挙する。"""
    if isinstance(data, Mapping):
        for key, value in data.items():
            yield from iter_secret_refs(value, (*path, str(key)))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            yield from iter_secret_refs(value, (*path, str(index)))
    elif is_secret_ref(data):
        yield path, secret_env_name(data)


def redact_config(data: Any) -> Any:
    """設定ツリーの Secret 参照を ``***`` に置き換えた新しいツリーを返す。"""
    if isinstance(data, Mapping):
        return {key: redact_config(value) for key, value in data.items()}
    if isinstance(data, list):
        return [redact_config(value) for value in data]
    if is_secret_ref(data):
        return REDACTED
    return data
