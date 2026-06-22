"""4.5 command queue（排他 claim / complete / fail）。"""

import unittest

from tests.support import make_sqlite, sample_command


class CommandQueueTest(unittest.TestCase):
    def setUp(self):
        self.storage = make_sqlite()
        self.addCleanup(self.storage.close)
        for i in range(3):
            self.storage.append_command(sample_command(f"cmd-{i}", f"idem-{i}"))

    def test_claim_marks_processing(self):
        claimed = self.storage.claim_pending_commands(limit=2)
        self.assertEqual(len(claimed), 2)
        self.assertTrue(all(c["status"] == "processing" for c in claimed))

    def test_claim_is_exclusive(self):
        # 逐次 claim でも同一 command は二重に割り当てられない（claim 済みは processing）
        first = {c["command_id"] for c in self.storage.claim_pending_commands(limit=2)}
        second = {c["command_id"] for c in self.storage.claim_pending_commands(limit=2)}
        self.assertEqual(first & second, set())
        self.assertEqual(len(first), 2)
        self.assertEqual(len(second), 1)  # 残り 1 件

    def test_complete_command(self):
        cmd = self.storage.claim_pending_commands(limit=1)[0]
        self.storage.complete_command(cmd["command_id"])
        row = self.storage.conn.execute(
            "SELECT status, processed_at FROM admin_commands WHERE command_id = ?",
            (cmd["command_id"],),
        ).fetchone()
        self.assertEqual(row["status"], "succeeded")
        self.assertIsNotNone(row["processed_at"])

    def test_fail_command(self):
        cmd = self.storage.claim_pending_commands(limit=1)[0]
        self.storage.fail_command(cmd["command_id"], "E_BOOM", "exploded")
        row = self.storage.conn.execute(
            "SELECT status, error_code, error_message, processed_at "
            "FROM admin_commands WHERE command_id = ?",
            (cmd["command_id"],),
        ).fetchone()
        self.assertEqual(row["status"], "failed")
        self.assertEqual(row["error_code"], "E_BOOM")
        self.assertEqual(row["error_message"], "exploded")
        self.assertIsNotNone(row["processed_at"])

    def test_claim_empty_returns_empty(self):
        self.storage.claim_pending_commands(limit=10)  # 全部 claim
        self.assertEqual(self.storage.claim_pending_commands(limit=10), [])


if __name__ == "__main__":
    unittest.main()
