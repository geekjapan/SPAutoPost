"""接続設定の最小読み込み。secret はログ/表示に出さない。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

# postgresql://user:password@host:port/db の password 部を隠す。
_URL_PASSWORD = re.compile(r"(://[^:/?#@]+:)([^@/?#]+)(@)")
# ?password=... または &password=... 形式（クエリパラメータ）。
_QUERY_PASSWORD = re.compile(r"([?&;])password=[^&;#\s]+", re.IGNORECASE)
# host=h user=u password=s3cr3t 形式（キーワード DSN）。
_KW_PASSWORD = re.compile(r"\bpassword=\S+", re.IGNORECASE)


def redact_url(url: str | None) -> str:
    """接続 URL / DSN の password を伏せた表示用文字列を返す。

    対応形式: ``user:pass@host``（URL）、``?password=s``（クエリパラメータ）、
    ``password=s``（キーワード DSN）。
    """
    if not url:
        return "(unset)"
    url = _URL_PASSWORD.sub(r"\1***\3", url)
    url = _QUERY_PASSWORD.sub(r"\1password=***", url)
    url = _KW_PASSWORD.sub("password=***", url)
    return url


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
