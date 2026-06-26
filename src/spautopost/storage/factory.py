"""``StorageConfig`` から backend を構築する factory。

正本: openspec/.../specs/storage-port「StorageConfig からのバックエンド選択」。

方針:
- アクティブ provider の必須フィールドを assert する
  (postgresql は ``database_url``、sqlite は ``sqlite_path``)。
- アクティブでない provider 向けのクロス provider フィールドが設定されている
  場合は ``StorageConfigError`` で顕在化する。
- psycopg は postgresql 分岐でのみ遅延 import する (sqlite 経路は psycopg 不在でも動作)。
- 未知 provider は防御的に ``StorageError`` (UnknownProviderError)。
- Secret 値 (database_url の中身等) は例外メッセージに含めない。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from ..config import StorageConfig
from ..secrets import is_secret_ref, secret_env_name
from .errors import StorageConfigError, UnknownProviderError
from .migrate import DEFAULT_MIGRATIONS_ROOT

if TYPE_CHECKING:
    from .port import StoragePort


def build_storage(
    config: StorageConfig,
    *,
    migrations_root: Path = DEFAULT_MIGRATIONS_ROOT,
) -> StoragePort:
    """検証済み ``StorageConfig`` から ``StoragePort`` を構築する。"""
    provider = config.provider
    if provider == "sqlite":
        return _build_sqlite(config, migrations_root)
    if provider == "postgresql":
        return _build_postgres(config, migrations_root)
    raise UnknownProviderError(f"unknown storage provider: {provider!r}")


def _build_sqlite(config: StorageConfig, migrations_root: Path) -> StoragePort:
    if not config.sqlite_path:
        raise StorageConfigError("storage.sqlite_path is required when provider=sqlite")
    if config.database_url:
        raise StorageConfigError(
            "storage.database_url must not be set when provider=sqlite (cross-provider field)"
        )
    from .sqlite_backend import build_sqlite_storage

    return build_sqlite_storage(config.sqlite_path, migrations_root=migrations_root)


def _build_postgres(config: StorageConfig, migrations_root: Path) -> StoragePort:
    if not config.database_url:
        raise StorageConfigError("storage.database_url is required when provider=postgresql")
    if config.sqlite_path:
        raise StorageConfigError(
            "storage.sqlite_path must not be set when provider=postgresql (cross-provider field)"
        )
    # psycopg は postgresql 分岐でのみ遅延 import する (sqlite 経路は不要)。
    from .postgres_backend import build_postgres_storage

    return build_postgres_storage(
        _resolve_database_url(config.database_url),
        migrations_root=migrations_root,
    )


def _resolve_database_url(database_url: str) -> str:
    """Resolve ``env:NAME`` database URL references at the storage boundary."""
    if not is_secret_ref(database_url):
        return database_url
    name = secret_env_name(database_url)
    resolved = os.environ.get(name)
    if not resolved:
        raise StorageConfigError(
            f"missing required secret env var: {name} (referenced at storage.database_url)"
        )
    return resolved
