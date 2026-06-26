"""4.6 PostgreSQL/SQLite adapter が同一 port API で同一結果を返すことの確認。

PostgreSQL は DATABASE_URL + psycopg がある時のみ実走。無ければ skip。
"""

import unittest

from tests.support import (
    make_postgres,
    make_sqlite,
    sample_command,
    sample_draft,
    sample_publication,
)


def exercise(storage, draft: dict | None = None, publication: dict | None = None) -> dict:
    """両 adapter で同一の port 操作列を実行し、観測結果を返す。"""
    draft = draft or sample_draft()
    publication = publication or sample_publication("pub-1", "draft-1", "idem-1")
    with storage:
        storage.save("draft_post", draft)
        storage.save("publication", publication)
        storage.append_command(sample_command("cmd-1", "cidem-1"))
        claimed = storage.claim_pending_commands(limit=5)
        storage.complete_command("cmd-1")
        return {
            "draft": storage.get("draft_post", "draft-1"),
            "publication": storage.get("publication", "pub-1"),
            "claimed_ids": [c["command_id"] for c in claimed],
            "claimed_status": [c["status"] for c in claimed],
        }


class ParityTest(unittest.TestCase):
    def test_sqlite_and_postgres_agree(self):
        draft = sample_draft()
        pub = sample_publication("pub-1", "draft-1", "idem-1")
        sqlite_result = exercise(make_sqlite(), draft, pub)
        pg = make_postgres()
        if pg is None:
            self.skipTest("DATABASE_URL/psycopg なし: PostgreSQL parity をスキップ")
        self.assertEqual(sqlite_result, exercise(pg, draft, pub))

    def test_sqlite_shape(self):
        # PG 不在でも port API の形を固定で検証
        result = exercise(make_sqlite())
        self.assertEqual(result["claimed_ids"], ["cmd-1"])
        self.assertEqual(result["claimed_status"], ["processing"])
        self.assertEqual(result["draft"]["status"], "created")
        self.assertEqual(result["publication"]["idempotency_key"], "idem-1")


if __name__ == "__main__":
    unittest.main()
