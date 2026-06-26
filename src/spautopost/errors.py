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
