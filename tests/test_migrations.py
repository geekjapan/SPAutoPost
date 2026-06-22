"""4.1 baseline migration 適用テスト（全テーブル/制約/index 生成）。"""

import unittest

from spautopost.storage import SqliteStorage
from spautopost.storage.migrate import apply_migrations
from tests.support import make_sqlite

EXPECTED_TABLES = {
    "source_records", "advisories", "draft_posts", "review_events",
    "publications", "audit_events", "admin_commands",
}


class MigrationTest(unittest.TestCase):
    def _names(self, conn, kind: str) -> set[str]:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = ?", (kind,)
        ).fetchall()
        return {r[0] for r in rows}

    def test_all_tables_created(self):
        with make_sqlite() as storage:
            tables = self._names(storage.conn, "table")
        self.assertTrue(EXPECTED_TABLES.issubset(tables), tables)

    def test_indexes_created(self):
        with make_sqlite() as storage:
            indexes = self._names(storage.conn, "index")
        self.assertIn("idx_draft_posts_status", indexes)
        self.assertIn("idx_admin_commands_status", indexes)

    def test_migration_is_idempotent(self):
        with SqliteStorage(":memory:") as storage:
            first = apply_migrations(storage.conn, "sqlite", placeholder="?")
            second = apply_migrations(storage.conn, "sqlite", placeholder="?")
        self.assertIn("0001_baseline", first)
        self.assertEqual(second, [])  # 再適用は何もしない


if __name__ == "__main__":
    unittest.main()
