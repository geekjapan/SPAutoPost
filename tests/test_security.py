"""5.2 Sensitive Data Policy: secret を保存しない / ログに出さない。"""

import re
import unittest

from spautopost.config import Config, load_config, redact_url
from spautopost.storage.migrate import migrations_dir, split_statements
from tests.support import make_sqlite

# data-model.md Sensitive Data Policy の保存禁止対象に対応する列名パターン。
SECRET_COLUMN = re.compile(
    r"(api_?key|access_?token|refresh_?token|client_?secret|private_?key"
    r"|password|cookie|authorization)",
    re.IGNORECASE,
)


class SecurityTest(unittest.TestCase):
    def test_no_secret_columns_in_schema(self):
        with make_sqlite() as storage:
            tables = [r[0] for r in storage.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            offenders = []
            for table in tables:
                for col in storage.conn.execute(f"PRAGMA table_info({table})").fetchall():
                    if SECRET_COLUMN.search(col[1]):
                        offenders.append(f"{table}.{col[1]}")
        self.assertEqual(offenders, [], f"secret 用の列を持ってはならない: {offenders}")

    def test_config_redacts_password(self):
        redacted = redact_url("postgresql://app:s3cr3t@db.example:5432/spautopost")
        self.assertNotIn("s3cr3t", redacted)
        self.assertIn("app", redacted)

    def test_config_repr_does_not_leak_secret(self):
        cfg = Config(database_url="postgresql://app:s3cr3t@db/spautopost")
        self.assertNotIn("s3cr3t", repr(cfg))

    def test_load_config_reads_env(self):
        cfg = load_config({"DATABASE_URL": "postgresql://h/db"})
        self.assertEqual(cfg.database_url, "postgresql://h/db")

    def test_postgres_migration_parses(self):
        # PG 正本 SQL が runner の splitter で文に分割できる（offline 健全性チェック）
        sql = (migrations_dir("postgres") / "0001_baseline.sql").read_text(encoding="utf-8")
        statements = split_statements(sql)
        creates = [s for s in statements if s.upper().startswith("CREATE TABLE")]
        self.assertEqual(len(creates), 7)  # 6 canonical entity + admin_commands


if __name__ == "__main__":
    unittest.main()
