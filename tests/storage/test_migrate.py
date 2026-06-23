"""migration ランナーのユニットテスト。

正本: openspec/.../specs/storage-migration。
SQLite (stdlib sqlite3) を実 DB として用い、PostgreSQL に依存しない。

網羅:
- 初回適用で schema_migrations ブートストラップ + version/checksum 記録。
- 再実行が no-op。
- チェックサム不一致 (ドリフト) で StorageError 送出・適用停止。
- 適用失敗時にロールバックし ledger に当該 version を残さない。
- 方言ディレクトリ選択 (postgres / sqlite)。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from spautopost.storage.errors import MigrationDriftError, StorageError
from spautopost.storage.migrate import (
    dialect_dir,
    iter_migration_files,
    pending_migrations,
    run_migrations,
)


def _make_migration(dir_path: Path, name: str, sql: str) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    target = dir_path / name
    target.write_text(sql, encoding="utf-8")
    return target


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r[0] for r in rows}


def test_dialect_dir_selects_by_provider(tmp_path: Path) -> None:
    root = tmp_path / "migrations"
    (root / "postgres").mkdir(parents=True)
    (root / "sqlite").mkdir(parents=True)
    assert dialect_dir(root, "sqlite").name == "sqlite"
    assert dialect_dir(root, "postgresql").name == "postgres"


def test_dialect_dir_rejects_unknown_provider(tmp_path: Path) -> None:
    with pytest.raises(StorageError):
        dialect_dir(tmp_path, "oracle")


def test_iter_migration_files_ascending(tmp_path: Path) -> None:
    d = tmp_path / "sqlite"
    _make_migration(d, "0002_second.sql", "SELECT 1;")
    _make_migration(d, "0001_baseline.sql", "SELECT 1;")
    files = iter_migration_files(d)
    assert [f.name for f in files] == ["0001_baseline.sql", "0002_second.sql"]


def test_first_apply_bootstraps_ledger(tmp_path: Path) -> None:
    root = tmp_path / "migrations"
    _make_migration(root / "sqlite", "0001_baseline.sql", "CREATE TABLE widgets (id TEXT);")
    conn = sqlite3.connect(":memory:")
    run_migrations(conn, root, "sqlite")
    assert "schema_migrations" in _table_names(conn)
    assert "widgets" in _table_names(conn)
    rows = conn.execute("SELECT version, checksum FROM schema_migrations").fetchall()
    assert [r[0] for r in rows] == ["0001_baseline"]
    assert rows[0][1]  # checksum 記録済み


def test_rerun_is_noop(tmp_path: Path) -> None:
    root = tmp_path / "migrations"
    _make_migration(root / "sqlite", "0001_baseline.sql", "CREATE TABLE widgets (id TEXT);")
    conn = sqlite3.connect(":memory:")
    run_migrations(conn, root, "sqlite")
    # 2 回目: 既に widgets があるので、再適用されれば "already exists" で失敗する。
    run_migrations(conn, root, "sqlite")
    count = conn.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    assert count == 1


def test_checksum_drift_halts(tmp_path: Path) -> None:
    root = tmp_path / "migrations"
    f = _make_migration(root / "sqlite", "0001_baseline.sql", "CREATE TABLE widgets (id TEXT);")
    conn = sqlite3.connect(":memory:")
    run_migrations(conn, root, "sqlite")
    # 適用済みファイルを改変 -> SHA-256 ドリフト。
    f.write_text("CREATE TABLE widgets (id TEXT, extra TEXT);", encoding="utf-8")
    with pytest.raises(MigrationDriftError):
        run_migrations(conn, root, "sqlite")


def test_pending_migrations_lists_unapplied_without_mutating(tmp_path: Path) -> None:
    root = tmp_path / "migrations"
    _make_migration(root / "sqlite", "0001_a.sql", "CREATE TABLE a (id TEXT);")
    _make_migration(root / "sqlite", "0002_b.sql", "CREATE TABLE b (id TEXT);")
    conn = sqlite3.connect(":memory:")

    # 何も適用していない -> 両方 pending。
    assert pending_migrations(conn, root, "sqlite") == ["0001_a", "0002_b"]
    # dry-run は DDL を適用しない（テーブル未作成のまま）。
    assert "a" not in _table_names(conn)

    run_migrations(conn, root, "sqlite")
    # 全適用後は pending 無し。
    assert pending_migrations(conn, root, "sqlite") == []


def test_pending_migrations_drift_halts(tmp_path: Path) -> None:
    root = tmp_path / "migrations"
    f = _make_migration(root / "sqlite", "0001_a.sql", "CREATE TABLE a (id TEXT);")
    conn = sqlite3.connect(":memory:")
    run_migrations(conn, root, "sqlite")
    f.write_text("CREATE TABLE a (id TEXT, x TEXT);", encoding="utf-8")
    with pytest.raises(MigrationDriftError):
        pending_migrations(conn, root, "sqlite")


def test_failure_rolls_back_and_no_ledger_row(tmp_path: Path) -> None:
    root = tmp_path / "migrations"
    _make_migration(root / "sqlite", "0001_ok.sql", "CREATE TABLE good (id TEXT);")
    _make_migration(
        root / "sqlite",
        "0002_bad.sql",
        "CREATE TABLE bad (id TEXT;",  # 構文エラー
    )
    conn = sqlite3.connect(":memory:")
    with pytest.raises(StorageError):
        run_migrations(conn, root, "sqlite")
    tables = _table_names(conn)
    assert "good" in tables  # 0001 はコミット済み
    assert "bad" not in tables  # 0002 はロールバック
    versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()]
    assert versions == ["0001_ok"]  # 失敗した 0002 は記録されない
