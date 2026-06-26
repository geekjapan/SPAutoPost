"""軽量 migration runner（Alembic 非依存）。

``db/migrations/<dialect>/*.sql`` を version 順に適用し、適用済みを
``schema_migrations`` で追跡する。SQL ファイル（手書き）が schema 正本。
"""

from __future__ import annotations

import os
from pathlib import Path

from .serialization import now_iso

# src/spautopost/storage/migrate.py -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]


def migrations_dir(dialect: str) -> Path:
    # SPAUTOPOST_MIGRATIONS_DIR が設定されている場合はそちらを優先する。
    # インストール済みパッケージ環境では _REPO_ROOT が repo root を指さないため。
    env_dir = os.environ.get("SPAUTOPOST_MIGRATIONS_DIR")
    if env_dir:
        return Path(env_dir) / dialect
    return _REPO_ROOT / "db" / "migrations" / dialect


def split_statements(sql: str) -> list[str]:
    """``;`` 区切りで文を分割し、コメント行を除去する。

    注意: 文字列リテラルや JSON 内に ``;`` が含まれる場合に誤って分割されます。
    migration ファイル内では文字列中に ``;`` を使用しないでください。
    """
    statements = []
    for chunk in sql.split(";"):
        lines = [ln for ln in chunk.splitlines() if not ln.strip().startswith("--")]
        stmt = "\n".join(lines).strip()
        if stmt:
            statements.append(stmt)
    return statements


def apply_migrations(conn, dialect: str, directory: Path | None = None,
                     placeholder: str = "?") -> list[str]:
    """未適用の migration を順に適用し、適用した version 一覧を返す。"""
    directory = directory or migrations_dir(dialect)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    cur.execute("SELECT version FROM schema_migrations")
    # psycopg の dict_row では row[0] が失敗するため row["version"] を使う。
    applied = {row["version"] for row in cur.fetchall()}

    sql_files = sorted(directory.glob("*.sql"))
    if not sql_files:
        raise FileNotFoundError(
            f"No SQL migration files found in {directory}. "
            "Set SPAUTOPOST_MIGRATIONS_DIR to the correct migrations path."
        )

    newly: list[str] = []
    for path in sql_files:
        version = path.stem
        if version in applied:
            continue
        cur.execute("BEGIN")
        try:
            for stmt in split_statements(path.read_text(encoding="utf-8")):
                cur.execute(stmt)
            cur.execute(
                f"INSERT INTO schema_migrations (version, applied_at) "
                f"VALUES ({placeholder}, {placeholder})",
                (version, now_iso()),
            )
        except Exception:
            cur.execute("ROLLBACK")
            raise
        cur.execute("COMMIT")
        newly.append(version)
    return newly
