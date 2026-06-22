"""4.3 CHECK 制約（enum 外を拒否）+ 4.4 UNIQUE（idempotency_key 重複拒否）。"""

import sqlite3
import unittest

from tests.support import (
    make_sqlite,
    sample_command,
    sample_draft,
    sample_publication,
)


class ConstraintTest(unittest.TestCase):
    def setUp(self):
        self.storage = make_sqlite()
        self.addCleanup(self.storage.close)

    def test_draft_status_check_rejects_unknown(self):
        bad = sample_draft()
        bad["status"] = "done"  # DraftStatus enum 外
        with self.assertRaises(sqlite3.IntegrityError):
            self.storage.save("draft_post", bad)

    def test_duplicate_publication_idempotency_rejected(self):
        self.storage.save("draft_post", sample_draft())
        self.storage.save("publication", sample_publication("pub-1", "draft-1", "idem-A"))
        with self.assertRaises(sqlite3.IntegrityError):
            self.storage.save("publication", sample_publication("pub-2", "draft-1", "idem-A"))

    def test_duplicate_command_idempotency_rejected(self):
        self.storage.append_command(sample_command("cmd-1", "cidem-A"))
        with self.assertRaises(sqlite3.IntegrityError):
            self.storage.append_command(sample_command("cmd-2", "cidem-A"))

    def test_independent_idempotency_scopes(self):
        # Publication と AdminCommand の idempotency_key は独立スコープ（同値でも衝突しない）
        self.storage.save("draft_post", sample_draft())
        self.storage.save("publication", sample_publication("pub-1", "draft-1", "shared"))
        self.storage.append_command(sample_command("cmd-1", "shared"))  # 例外が出なければ OK
        self.assertIsNotNone(self.storage.get("publication", "pub-1"))


if __name__ == "__main__":
    unittest.main()
