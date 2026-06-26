"""Microsoft Graph delegated PoC 経路の例外。

Secret（access token / client secret 等）は例外メッセージに含めない。
"""

from __future__ import annotations


class GraphError(Exception):
    """Graph 経路エラーの基底。"""


class GraphAuthError(GraphError):
    """delegated 認証（device code flow）の失敗。"""


class GraphApiError(GraphError):
    """Graph API 呼び出しの失敗。HTTP status と retry 可否を保持する。"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
