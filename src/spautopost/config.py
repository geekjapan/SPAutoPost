"""接続設定の最小読み込み。secret はログ/表示に出さない。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

# postgresql://user:password@host:port/db の password 部を隠す。
_URL_PASSWORD = re.compile(r"(://[^:/?#@]+:)([^@/?#]+)(@)")


def redact_url(url: str | None) -> str:
    """接続 URL の password を伏せた表示用文字列を返す。"""
    if not url:
        return "(unset)"
    return _URL_PASSWORD.sub(r"\1***\3", url)


@dataclass(frozen=True)
class Config:
    """storage 接続設定。database_url は secret を含みうるので repr で伏せる。"""

    database_url: str | None = None

    def __repr__(self) -> str:  # secret をログに漏らさない
        return f"Config(database_url={redact_url(self.database_url)!r})"


def load_config(env: dict[str, str] | None = None) -> Config:
    """環境変数から設定を読み込む（`DATABASE_URL`）。"""
    source = os.environ if env is None else env
    return Config(database_url=source.get("DATABASE_URL"))
