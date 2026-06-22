"""JSON と timestamp の正規化ヘルパ。

timestamp は port で UTC へ正規化する:
- SQLite: ISO8601 UTC TEXT として保存
- PostgreSQL: timezone-aware datetime(UTC) として渡し timestamptz へ
read 時はどちらも ISO8601 UTC 文字列に揃える（adapter 間で同一結果）。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone


def now_iso() -> str:
    """現在時刻を ISO8601 UTC 文字列で返す。"""
    return datetime.now(timezone.utc).isoformat()


def to_utc_datetime(value):
    """str / datetime を timezone-aware な UTC datetime に正規化する。"""
    if value is None:
        return None
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_iso_utc(value):
    """str / datetime を ISO8601 UTC 文字列に正規化する。"""
    dt = to_utc_datetime(value)
    return dt.isoformat() if dt is not None else None


def dumps_json(obj) -> str:
    """JSON 列用に dict/list を文字列化する（SQLite）。"""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def loads_json(value):
    """JSON 列の値を Python へ復元する。dict/list ならそのまま返す（PG JSONB）。"""
    if value is None:
        return {}
    if isinstance(value, (dict, list)):
        return value
    return json.loads(value)
