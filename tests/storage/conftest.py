"""ストレージ contract suite 共有フィクスチャ。

backend は段階的に追加する。``BACKEND_FACTORIES`` に (id, factory) を追記すると、
共有 contract suite が自動的にその backend をパラメタライズ対象に含める。

各 factory は引数として pytest の ``tmp_path`` を受け取り、migration 適用済みの
``StoragePort`` を返す callable。PostgreSQL backend は
``SPAUTOPOST_TEST_DATABASE_URL`` が無い CI 外環境では skip する（spec の方針）。

現時点（TASK BLOCK 1）では backend 実装が未着手のため、ファクトリ登録は空であり、
contract suite は RED（未提供のため失敗/skip）となるのが期待状態。
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from spautopost.storage.port import StoragePort

# backend factory の型: tmp_path を受け取り migration 適用済み StoragePort を返す。
BackendFactory = Callable[[Path], "StoragePort"]


def _build_sqlite_backend(tmp_path: Path) -> StoragePort:
    """SQLite backend の factory（migration 適用済み StoragePort を返す）。"""
    from spautopost.config import StorageConfig
    from spautopost.storage.factory import build_storage

    db_path = str(tmp_path / "contract.sqlite3")
    port = build_storage(StorageConfig(provider="sqlite", database_url=None, sqlite_path=db_path))
    port.migrate()
    return port


# PG はテスト間で同一 DB を再利用するため、各テスト前にデータを掃除する
# (SQLite は tmp ファイルで自然に分離される)。schema_migrations は残す。
_PG_DATA_TABLES = (
    "source_records",
    "advisories",
    "draft_posts",
    "review_events",
    "publications",
    "audit_events",
)


def _build_postgres_backend(tmp_path: Path) -> StoragePort:
    """PostgreSQL backend の factory（CI でのみ実行）。テスト分離のため毎回 TRUNCATE。"""
    from spautopost.config import StorageConfig
    from spautopost.storage.factory import build_storage

    database_url = os.environ["SPAUTOPOST_TEST_DATABASE_URL"]
    port = build_storage(
        StorageConfig(provider="postgresql", database_url=database_url, sqlite_path=None)
    )
    port.migrate()
    conn = port._conn  # type: ignore[attr-defined]  # テスト分離のための掃除
    with conn.cursor() as cur:
        cur.execute(
            "TRUNCATE " + ", ".join(_PG_DATA_TABLES) + " RESTART IDENTITY CASCADE"  # noqa: S608
        )
    conn.commit()
    return port


# (id, factory, needs_postgres) のリスト。backend 実装の進捗に応じて追記する。
BACKEND_SPECS: list[tuple[str, BackendFactory, bool]] = [
    ("sqlite", _build_sqlite_backend, False),
    ("postgres", _build_postgres_backend, True),  # CI (PG service) でのみ実行
]


def _make_backend_params() -> list[pytest.param]:  # type: ignore[type-arg]
    params: list[pytest.param] = []  # type: ignore[type-arg]
    has_pg_url = bool(os.environ.get("SPAUTOPOST_TEST_DATABASE_URL"))
    for backend_id, factory, needs_pg in BACKEND_SPECS:
        marks = []
        if needs_pg and not has_pg_url:
            marks.append(
                pytest.mark.skipif(True, reason="no postgres (SPAUTOPOST_TEST_DATABASE_URL unset)")
            )
        params.append(pytest.param(factory, id=backend_id, marks=marks))
    return params


@pytest.fixture(params=_make_backend_params())
def storage(request: pytest.FixtureRequest, tmp_path: Path) -> StoragePort:
    """登録済み backend ごとに migration 適用済み StoragePort を提供する。

    backend が 1 つも登録されていない場合、このフィクスチャに依存するテストは
    pytest によって「パラメータ無し」として収集され、未実装＝RED を表す。
    """
    factory: BackendFactory = request.param
    port = factory(tmp_path)
    yield port
    port.close()
