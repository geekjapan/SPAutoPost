"""PostgreSQL adapter（正本 DB）。psycopg は遅延 import。

claim は ``FOR UPDATE SKIP LOCKED``、JSON は JSONB、timestamp は timestamptz。
``DATABASE_URL`` と psycopg が揃う環境でのみ実走する。
"""

from __future__ import annotations

from .migrate import apply_migrations
from .port import _SqlStorage
from .serialization import to_utc_datetime


class PostgresStorage(_SqlStorage):
    PH = "%s"
    DIALECT = "postgres"

    def __init__(self, dsn: str):
        import psycopg  # 遅延 import
        from psycopg.rows import dict_row

        self.conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)

    def _json_param(self, obj):
        from psycopg.types.json import Jsonb

        return Jsonb(obj)

    def _ts_param(self, value):
        return to_utc_datetime(value)  # timestamptz には aware datetime を渡す

    def migrate(self) -> None:
        apply_migrations(self.conn, self.DIALECT, placeholder=self.PH)

    def claim_pending_commands(self, limit: int = 10) -> list[dict]:
        # autocommit でも FOR UPDATE のロックを保つため明示トランザクション。
        with self.conn.transaction():
            cur = self.conn.cursor()
            cur.execute(
                "SELECT * FROM admin_commands WHERE status='pending' "
                "ORDER BY created_at, command_id LIMIT %s FOR UPDATE SKIP LOCKED",
                (limit,),
            )
            rows = cur.fetchall()
            ids = [r["command_id"] for r in rows]
            if ids:
                cur.execute(
                    "UPDATE admin_commands SET status='processing' "
                    "WHERE command_id = ANY(%s)",
                    (ids,),
                )
        return [{**self._command_from_row(r), "status": "processing"} for r in rows]
