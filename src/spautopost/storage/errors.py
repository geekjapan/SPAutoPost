"""ストレージレイヤの例外階層。

Secret 値（API key / token / client secret / database_url の認証情報等）は
例外メッセージに含めない（フィールド名・provider 名・制約名のみ）。

階層:
- StorageError                基底
  - ConstraintViolationError  NOT NULL / UNIQUE / CHECK / FK 等の制約違反、境界拒否
  - MigrationDriftError       migration チェックサムドリフト・スキーマ等価ドリフト
  - StorageConfigError        設定不整合（必須フィールド欠如・クロス provider フィールド）
  - UnknownProviderError      未知の provider（防御用）
"""

from __future__ import annotations


class StorageError(Exception):
    """ストレージ関連エラーの基底。"""


class ConstraintViolationError(StorageError):
    """制約違反（NOT NULL / UNIQUE / CHECK / FK）と境界での値拒否。

    naive datetime / null・空 idempotency_key の境界拒否もここに含める。
    """


class MigrationDriftError(StorageError):
    """migration の SHA-256 ドリフト、または二方言スキーマ等価のドリフト。"""


class StorageConfigError(StorageError):
    """設定不整合（必須フィールド欠如・アクティブでない provider のフィールド指定）。"""


class UnknownProviderError(StorageError):
    """未知の provider 値（通常 config validation で到達しないが防御用）。"""
