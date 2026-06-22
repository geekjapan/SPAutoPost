"""4.2 entity round-trip（保存→取得一致、JSON ネスト復元）+ 3.5 model 表現。"""

import unittest
from dataclasses import asdict

from spautopost.models import DraftPost
from spautopost.storage.serialization import to_iso_utc
from tests.support import make_sqlite, sample_draft


class RoundTripTest(unittest.TestCase):
    def setUp(self):
        self.storage = make_sqlite()
        self.addCleanup(self.storage.close)

    def test_draft_roundtrip(self):
        draft = sample_draft()
        self.storage.save("draft_post", draft)
        got = self.storage.get("draft_post", "draft-1")
        # timestamp は UTC ISO に正規化されて返る
        expected = {**draft, "created_at": to_iso_utc(draft["created_at"]),
                    "updated_at": to_iso_utc(draft["updated_at"])}
        self.assertEqual(got, expected)

    def test_nested_json_restored(self):
        draft = sample_draft()
        self.storage.save("draft_post", draft)
        got = self.storage.get("draft_post", "draft-1")
        # ネスト構造（references / advisory_ids）が JSON 経由で復元される
        self.assertEqual(got["references"], draft["references"])
        self.assertEqual(got["advisory_ids"], ["adv-1", "adv-2"])

    def test_get_missing_returns_none(self):
        self.assertIsNone(self.storage.get("draft_post", "nope"))

    def test_save_is_upsert(self):
        self.storage.save("draft_post", sample_draft(status="created"))
        self.storage.save("draft_post", sample_draft(status="approved"))
        self.assertEqual(self.storage.get("draft_post", "draft-1")["status"], "approved")

    def test_dataclass_model_roundtrip(self):
        # 3.5: 薄い model 表現が asdict 経由で port にそのまま渡せる
        model = DraftPost(
            draft_id="draft-9", title="t", audience="mixed", urgency="normal",
            summary_for_users="s", impact="i", status="generated",
            created_at="2026-06-23T00:00:00+00:00", updated_at="2026-06-23T00:00:00+00:00",
            advisory_ids=["a1"],
        )
        self.storage.save("draft_post", asdict(model))
        got = self.storage.get("draft_post", "draft-9")
        self.assertEqual(got["status"], "generated")
        self.assertEqual(got["advisory_ids"], ["a1"])


if __name__ == "__main__":
    unittest.main()
