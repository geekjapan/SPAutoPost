"""最小 migration ランナー (SQL ファースト・チェックサム込み)。

正本: openspec/.../specs/storage-migration。

方針:
- schema 正本は方言別の SQL migration ファイル
  (db/migrations/{postgres,sqlite}/NNNN_*.sql)。ORM 自動生成に依存しない。
- ``schema_migrations(version, checksum, applied_at)`` をランナーが
  ``CREATE TABLE IF NOT EXISTS`` で冪等にブートストラップする
  (番号付き migration ファイルの外で行う)。
- 1 ファイル 1 トランザクション: BEGIN -> SQL 適用 -> ledger INSERT -> COMMIT。
  失敗時はロールバックし、当該 version を ledger に残さない。
- version 昇順で適用。適用済みは再適用しない (再実行は no-op)。
- 適用済みファイルから SHA-256 を再計算し、ledger と不一致なら
  ``MigrationDriftError`` を送出して停止する。

ドライバ非依存: DB-API 2.0 互換 connection を受け取る。sqlite3 / psycopg の
双方で動作する (psycopg は postgres 分岐でのみ遅延 import されるため、本
モジュール自体は psycopg を import しない)。
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .errors import MigrationDriftError, StorageError

# provider -> 方言ディレクトリ名のマッピング (正本)。
_PROVIDER_DIALECT_DIRS: dict[str, str] = {
    "postgresql": "postgres",
    "sqlite": "sqlite",
}

# プロジェクトルートからの既定 migration ルート (db/migrations)。
DEFAULT_MIGRATIONS_ROOT = Path(__file__).resolve().parents[3] / "db" / "migrations"


class _DBAPIConnection(Protocol):
    """ランナーが必要とする最小の DB-API 2.0 connection インターフェース。"""

    def cursor(self) -> Any: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


def dialect_dir(migrations_root: Path, provider: str) -> Path:
    """provider に対応する方言ディレクトリ Path を返す。

    未知 provider は ``StorageError`` (防御用)。
    """
    dirname = _PROVIDER_DIALECT_DIRS.get(provider)
    if dirname is None:
        raise StorageError(f"unknown storage provider for migrations: {provider!r}")
    return migrations_root / dirname


def iter_migration_files(dialect_path: Path) -> list[Path]:
    """方言ディレクトリ内の ``*.sql`` を version (ファイル名) 昇順で返す。"""
    if not dialect_path.is_dir():
        return []
    return sorted(dialect_path.glob("*.sql"), key=lambda p: p.name)


def _version_of(path: Path) -> str:
    """ファイル名から version 文字列を導出する (拡張子を除いた stem)。"""
    return path.stem


def _checksum_of(path: Path) -> str:
    """ファイル内容の SHA-256 (hex) を返す。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bootstrap_ledger(conn: _DBAPIConnection) -> None:
    """schema_migrations を冪等にブートストラップする (番号付きファイルの外)。"""
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version TEXT PRIMARY KEY, "
        "checksum TEXT NOT NULL, "
        "applied_at TEXT NOT NULL)"
    )
    conn.commit()


def _applied_checksums(conn: _DBAPIConnection) -> dict[str, str]:
    """ledger 済みの {version: checksum} を返す。"""
    cur = conn.cursor()
    cur.execute("SELECT version, checksum FROM schema_migrations")
    return {row[0]: row[1] for row in cur.fetchall()}


def _execute_sql_script(cur: Any, sql: str) -> None:
    """SQL スクリプト (複数文) を実行する。

    sqlite3 の cursor は ``executescript`` を持ち暗黙コミットを伴うため使わず、
    psycopg / sqlite3 双方で動く逐次 ``execute`` でステートメント分割実行する。
    本リポジトリの baseline は文字列リテラルにセミコロンを含まないため、単純な
    ``;`` 分割で安全に分割できる。
    """
    for statement in _split_statements(sql):
        cur.execute(statement)


def _split_statements(sql: str) -> list[str]:
    """SQL を ``;`` 区切りのステートメントへ分割する (空文・コメント行を除外)。"""
    statements: list[str] = []
    for chunk in sql.split(";"):
        stripped = _strip_sql_comments(chunk).strip()
        if stripped:
            statements.append(stripped)
    return statements


def _strip_sql_comments(chunk: str) -> str:
    """行頭/行中の ``--`` 行コメントを除去する (単純な行ベース)。"""
    lines: list[str] = []
    for line in chunk.splitlines():
        idx = line.find("--")
        lines.append(line if idx < 0 else line[:idx])
    return "\n".join(lines)


def _apply_one(conn: _DBAPIConnection, path: Path, placeholder: str) -> None:
    """単一 migration ファイルを 1 トランザクションで適用し ledger に記録する。

    失敗時はロールバックし、ledger に当該 version を残さない。
    ``placeholder`` は方言別のパラメタプレースホルダ (sqlite3=``?``, psycopg=``%s``)。
    """
    version = _version_of(path)
    checksum = _checksum_of(path)
    sql = path.read_text(encoding="utf-8")
    cur = conn.cursor()
    try:
        _execute_sql_script(cur, sql)
        ph = placeholder
        cur.execute(
            # ph はプレースホルダ定数 (?/%s)。値は常にパラメタ。S608 は誤検知。
            "INSERT INTO schema_migrations (version, checksum, applied_at) "  # noqa: S608
            f"VALUES ({ph}, {ph}, {ph})",
            (version, checksum, datetime.now(UTC).isoformat(timespec="seconds")),
        )
        conn.commit()
    except Exception as exc:  # noqa: BLE001 - 全失敗をロールバックして包む
        conn.rollback()
        if isinstance(exc, StorageError):
            raise
        raise StorageError(f"migration failed and was rolled back: {version}") from exc


def pending_migrations(
    conn: _DBAPIConnection,
    migrations_root: Path,
    provider: str,
) -> list[str]:
    """未適用 migration の version リストを version 昇順で返す（DDL は適用しない）。

    dry-run 用。``schema_migrations`` ledger を冪等にブートストラップした上で、
    ディスク上の migration ファイルのうち ledger 未記録のものを列挙する。
    適用済みファイルのチェックサムドリフトを検知した場合は
    ``MigrationDriftError`` を送出する（apply 前に異常を顕在化させる）。
    """
    dpath = dialect_dir(migrations_root, provider)
    _bootstrap_ledger(conn)
    applied = _applied_checksums(conn)
    pending: list[str] = []
    for path in iter_migration_files(dpath):
        version = _version_of(path)
        if version in applied:
            if applied[version] != _checksum_of(path):
                raise MigrationDriftError(
                    f"checksum drift detected for migration {version}; "
                    "applied content differs from ledger"
                )
            continue
        pending.append(version)
    return pending


def run_migrations(
    conn: _DBAPIConnection,
    migrations_root: Path,
    provider: str,
    *,
    placeholder: str = "?",
) -> list[str]:
    """provider に応じた方言の baseline を昇順適用する。

    戻り値は本実行で新規適用した version のリスト (再実行 no-op 時は空)。
    適用済みファイルのチェックサムドリフトを検知した場合は
    ``MigrationDriftError`` を送出して停止する。
    ``placeholder`` は ledger INSERT のパラメタプレースホルダ
    (sqlite3=``?`` 既定, psycopg=``%s``)。
    """
    dpath = dialect_dir(migrations_root, provider)
    _bootstrap_ledger(conn)
    applied = _applied_checksums(conn)
    newly_applied: list[str] = []

    for path in iter_migration_files(dpath):
        version = _version_of(path)
        current = _checksum_of(path)
        if version in applied:
            if applied[version] != current:
                raise MigrationDriftError(
                    f"checksum drift detected for migration {version}; "
                    "applied content differs from ledger"
                )
            continue  # 適用済み & 一致 -> no-op
        _apply_one(conn, path, placeholder)
        newly_applied.append(version)

    return newly_applied
