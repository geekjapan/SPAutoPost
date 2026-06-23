"""``build_storage`` factory の単体テスト。

正本: openspec/.../specs/storage-port「StorageConfig からのバックエンド選択」。

検証観点:
- sqlite provider は ``SQLiteStorage`` を返す。
- 必須フィールド欠如は ``StorageConfigError``。
- アクティブでない provider のクロスフィールド指定は ``StorageConfigError``。
- 未知 provider は ``UnknownProviderError``。
- postgresql 分岐は psycopg 不在環境でも import 可能で、psycopg 未導入時は
  ``StorageError`` を送出する（factory の import 自体は失敗しない）。
- 例外メッセージに Secret 値（database_url の認証情報）を含めない。
"""

from __future__ import annotations

import importlib.util

import pytest

from spautopost.config import StorageConfig
from spautopost.storage.errors import StorageConfigError, StorageError, UnknownProviderError
from spautopost.storage.factory import build_storage

_HAS_PSYCOPG = importlib.util.find_spec("psycopg") is not None


def test_build_sqlite_returns_sqlite_storage(tmp_path: object) -> None:
    from spautopost.storage.sqlite_backend import SQLiteStorage

    config = StorageConfig(
        provider="sqlite",
        database_url=None,
        sqlite_path=str(tmp_path) + "/factory.sqlite3",
    )

    port = build_storage(config)

    assert isinstance(port, SQLiteStorage)
    port.close()


def test_sqlite_requires_sqlite_path() -> None:
    config = StorageConfig(provider="sqlite", database_url=None, sqlite_path=None)

    with pytest.raises(StorageConfigError, match="sqlite_path is required"):
        build_storage(config)


def test_sqlite_rejects_cross_provider_database_url() -> None:
    config = StorageConfig(
        provider="sqlite",
        database_url="postgresql://x/y",
        sqlite_path="/tmp/x.sqlite3",  # noqa: S108 - テスト用ダミーパス
    )

    with pytest.raises(StorageConfigError, match="database_url must not be set"):
        build_storage(config)


def test_postgres_requires_database_url() -> None:
    config = StorageConfig(provider="postgresql", database_url=None, sqlite_path=None)

    with pytest.raises(StorageConfigError, match="database_url is required"):
        build_storage(config)


def test_postgres_rejects_cross_provider_sqlite_path() -> None:
    config = StorageConfig(
        provider="postgresql",
        database_url="postgresql://x/y",
        sqlite_path="/tmp/x.sqlite3",  # noqa: S108 - テスト用ダミーパス
    )

    with pytest.raises(StorageConfigError, match="sqlite_path must not be set"):
        build_storage(config)


def test_unknown_provider_raises_unknown_provider_error() -> None:
    config = StorageConfig(provider="mysql", database_url=None, sqlite_path=None)

    with pytest.raises(UnknownProviderError, match="unknown storage provider"):
        build_storage(config)


@pytest.mark.skipif(_HAS_PSYCOPG, reason="psycopg installed; lazy-import error path unavailable")
def test_postgres_without_psycopg_raises_storage_error() -> None:
    """psycopg 未導入環境では postgresql 分岐は ``StorageError`` を送出する。

    factory モジュール自体は psycopg を import しないため、import は成功し、
    build 時にのみ遅延 import が失敗して顕在化することを確認する。
    """
    secret_url = "postgresql://user:s3cr3t@db.internal/spautopost"  # noqa: S105 - テスト用ダミー
    config = StorageConfig(provider="postgresql", database_url=secret_url, sqlite_path=None)

    with pytest.raises(StorageError) as excinfo:
        build_storage(config)

    message = str(excinfo.value)
    assert "psycopg" in message
    # Secret 値（パスワード・接続文字列）が例外メッセージへ漏れない。
    assert "s3cr3t" not in message
    assert secret_url not in message


@pytest.mark.skipif(
    not _HAS_PSYCOPG, reason="psycopg not installed; OperationalError path unavailable"
)
def test_postgres_connect_error_does_not_leak_url() -> None:
    """接続失敗 (OperationalError) は Secret 非含有の ``StorageError`` に正規化される。

    到達不能ポートへ秘密値入り database_url で接続し、例外メッセージへ
    パスワード・接続文字列が漏れないことを確認する。psycopg 導入環境でのみ実行。
    """
    # ポート 1 は通常閉じており接続が即失敗する。パスワードはダミー。
    secret_url = "postgresql://user:s3cr3t@127.0.0.1:1/spautopost"  # noqa: S105 - テスト用ダミー
    config = StorageConfig(provider="postgresql", database_url=secret_url, sqlite_path=None)

    with pytest.raises(StorageError) as excinfo:
        build_storage(config)

    message = str(excinfo.value)
    assert "s3cr3t" not in message
    assert secret_url not in message
