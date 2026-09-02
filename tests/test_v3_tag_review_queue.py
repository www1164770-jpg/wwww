import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from scripts.prepare_v3_tag_review_queue import prepare_queue, validate_queue  # noqa: E402
from scripts.summarize_v3_tag_review import summarize  # noqa: E402


class V3TagReviewQueueTests(unittest.TestCase):
    def setUp(self):
        self.candidates = ROOT / "docs" / "recommendation" / "v3-tag-candidates.json"

    def test_queue_starts_unapproved_and_contains_all_candidates(self):
        queue = prepare_queue(self.candidates)
        self.assertEqual(len(queue["items"]), 46)
        self.assertTrue(all(item["review_status"] == "needs_review" for item in queue["items"]))
        self.assertFalse(queue["database_write_performed"])
        self.assertEqual(validate_queue(queue), [])
        summary = summarize(queue)
        self.assertTrue(summary["status_sum_ok"])
        self.assertFalse(summary["ready_for_migration_preview"])
        self.assertEqual(summary["needs_review"], 46)

    def test_approved_item_requires_all_review_checks_and_a_tag(self):
        queue = prepare_queue(self.candidates)
        item = queue["items"][0]
        item["review_status"] = "approved"
        self.assertTrue(validate_queue(queue))
        item["approved_tags"] = [item["suggested_tags"][0]]
        item["review_checks"] = {key: True for key in item["review_checks"]}
        self.assertEqual(validate_queue(queue), [])

    def test_rejected_item_must_record_rejected_tags(self):
        queue = prepare_queue(self.candidates)
        queue["items"][0]["review_status"] = "rejected"
        self.assertTrue(validate_queue(queue))
        queue["items"][0]["rejected_tags"] = [queue["items"][0]["suggested_tags"][0]]
        self.assertEqual(validate_queue(queue), [])


if __name__ == "__main__":
    unittest.main()
