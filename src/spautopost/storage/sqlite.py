"""SQLite adapter（local/test substrate）。JSON は TEXT、timestamp は ISO8601 UTC TEXT。"""

from __future__ import annotations

import sqlite3

from .migrate import apply_migrations
from .port import _SqlStorage


class SqliteStorage(_SqlStorage):
    PH = "?"
    DIALECT = "sqlite"

    def __init__(self, path: str = ":memory:"):
        # isolation_level=None: autocommit。claim だけ明示 BEGIN IMMEDIATE で排他。
        self.conn = sqlite3.connect(path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def migrate(self) -> None:
        apply_migrations(self.conn, self.DIALECT, placeholder=self.PH)

    def claim_pending_commands(self, limit: int = 10) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute("BEGIN IMMEDIATE")  # 書き込みロックで claim を直列化
        try:
            cur.execute(
                "SELECT * FROM admin_commands WHERE status='pending' "
                "ORDER BY created_at, command_id LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
            ids = [r["command_id"] for r in rows]
            if ids:
                marks = ",".join(["?"] * len(ids))
                cur.execute(
                    f"UPDATE admin_commands SET status='processing' "
                    f"WHERE command_id IN ({marks})",
                    ids,
                )
            cur.execute("COMMIT")
        except Exception:
            cur.execute("ROLLBACK")
            raise
        return [{**self._command_from_row(r), "status": "processing"} for r in rows]
