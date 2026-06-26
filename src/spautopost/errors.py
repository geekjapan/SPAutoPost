"""SPAutoPost の設定関連例外。

Secret 値は例外メッセージに含めない（変数名のみ）。
"""

from __future__ import annotations


class ConfigError(Exception):
    """設定関連エラーの基底。"""


class ConfigValidationError(ConfigError):
    """config validation の失敗。複数の問題をまとめて保持する。"""

    def __init__(self, issues: list[str]) -> None:
        self.issues: list[str] = list(issues)
        detail = "\n".join(f"- {issue}" for issue in self.issues)
        super().__init__(f"config validation failed:\n{detail}")


class PublishError(Exception):
    """SharePoint publish の失敗（状態不正・Graph API エラー等）。"""


class GraphAuthError(Exception):
    """Microsoft Graph 認証情報の不足または不正。"""


class InvalidTransitionError(Exception):
    """DraftPost の不正な状態遷移。"""

    def __init__(self, previous_status: str, action: str, attempted_status: str) -> None:
        self.previous_status = previous_status
        self.action = action
        self.attempted_status = attempted_status
        super().__init__(
            f"invalid transition: {previous_status!r} + {action!r}"
            f" → {attempted_status!r} is not allowed"
        )


class PublishGateError(Exception):
    """承認されていない DraftPost の publish 試行。"""

    def __init__(self, draft_id: str, actual_status: str) -> None:
        self.draft_id = draft_id
        self.actual_status = actual_status
        super().__init__(
            f"draft {draft_id!r} cannot be published:"
            f" status is {actual_status!r}, expected 'approved'"
        )
