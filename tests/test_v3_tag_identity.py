from copy import deepcopy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]
from v3_tag_identity import resolve_review_queue
from resource_migration import approved_tag_plan


def approved(sid=1, name="Product", url="https://EXAMPLE.test/Product"):
    return {"website_id": sid, "website": name, "url": url, "signal": "api_debugging",
        "suggested_tags": ["api_debugging", "testing"], "approved_tags": ["api_debugging"],
        "rejected_tags": ["testing"], "review_status": "approved", "review_note": "Synthetic fixture evidence",
        "candidate_reason": "fixture", "review_checks": {key: True for key in
        ("capability_confirmed", "tag_specific", "no_profile_pollution", "evidence_clear")}}


class TagIdentityTests(unittest.TestCase):
    def setUp(self):
        self.queue = {"items": [approved()]}
        self.data = {"websites": [{"id": 100, "name": "Product", "url": "https://example.test/Product", "status": "approved"}],
                     "tags": [], "site_tags": [], "site_occupations": []}

    def test_complete_url_and_name_rebind_id_preserving_approval(self):
        before = deepcopy(self.queue)
        report, mapped = resolve_review_queue(self.queue, self.data)
        self.assertEqual(report["summary"]["reliably_mapped"], 1)
        self.assertEqual(mapped["items"][0]["website_id"], 100)
        self.assertEqual(self.queue, before)
        plan = approved_tag_plan(mapped, self.data, source_queue=self.queue)
        self.assertEqual([row["tag"] for row in plan], ["api_debugging"])
        self.assertEqual(plan[0]["identity_mapping"]["old"]["id"], 1)

    def test_host_name_description_and_path_case_never_suffice(self):
        for url in ("https://example.test/product", "https://example.test/Other", "https://example.test/Product?x=1", "https://other.test/Product"):
            with self.subTest(url=url):
                self.data["websites"][0].update(url=url, description="same duplicated description")
                report, _ = resolve_review_queue(self.queue, self.data)
                self.assertEqual(report["summary"]["reliably_mapped"], 0)

    def test_same_id_different_product_is_not_trusted(self):
        self.data["websites"][0].update(id=1, name="Other Product", url="https://example.test/Other")
        report, _ = resolve_review_queue(self.queue, self.data)
        self.assertEqual(report["rows"][0]["status"], "unresolved")

    def test_duplicate_url_targets_are_ambiguous(self):
        self.data["websites"].append({**self.data["websites"][0], "id": 101})
        report, _ = resolve_review_queue(self.queue, self.data)
        self.assertEqual(report["rows"][0]["conflict_reason"], "ambiguous_full_url")

    def test_duplicate_reviews_share_one_operation(self):
        self.queue["items"].append(approved(sid=2))
        report, mapped = resolve_review_queue(self.queue, self.data)
        self.assertEqual(report["summary"]["no_migration_duplicate_review"], 1)
        self.assertEqual(len(approved_tag_plan(mapped, self.data, source_queue=self.queue)), 1)

    def test_existing_approved_link_needs_no_migration(self):
        self.data["tags"] = [{"id": 7, "name": "api_debugging"}]
        self.data["site_tags"] = [{"id": 8, "site_id": 100, "tag_id": 7}]
        report, _ = resolve_review_queue(self.queue, self.data)
        self.assertEqual(report["summary"]["no_migration_existing"], 1)
        self.assertEqual(report["summary"]["unique_pending_associations"], 0)

    def test_mapped_tag_or_evidence_tampering_is_rejected(self):
        _, mapped = resolve_review_queue(self.queue, self.data)
        for field, value in [("approved_tags", ["testing"]), ("review_note", "rewritten approval"), ("website_id", 999)]:
            tampered = deepcopy(mapped)
            tampered["items"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                approved_tag_plan(tampered, self.data, source_queue=self.queue)

    def test_original_queue_and_current_catalog_are_rechecked(self):
        _, mapped = resolve_review_queue(self.queue, self.data)
        with self.assertRaises(ValueError):
            approved_tag_plan(mapped, self.data)
        changed = deepcopy(self.queue)
        changed["items"][0]["review_note"] = "changed"
        with self.assertRaises(ValueError):
            approved_tag_plan(mapped, self.data, source_queue=changed)
        self.data["websites"][0]["url"] += "/changed"
        with self.assertRaises(ValueError):
            approved_tag_plan(mapped, self.data, source_queue=self.queue)

    def test_existing_mixed_case_code_is_reused_without_renaming(self):
        item = self.queue["items"][0]
        item.update(signal="deployment", suggested_tags=["devops"], approved_tags=["devops"], rejected_tags=[])
        self.data["tags"] = [{"id": 7, "name": "DevOps"}]
        self.data["site_tags"] = [{"id": 8, "site_id": 100, "tag_id": 7}]
        report, mapped = resolve_review_queue(self.queue, self.data)
        self.assertEqual(report["summary"]["no_migration_existing"], 1)
        self.assertTrue(approved_tag_plan(mapped, self.data, source_queue=self.queue)[0]["already_present"])
        self.assertEqual(self.data["tags"][0]["name"], "DevOps")

    def test_case_normalized_duplicate_codes_are_rejected(self):
        self.data["tags"] = [{"id": 7, "name": "DevOps"}, {"id": 8, "name": "devops"}]
        _, mapped = resolve_review_queue(self.queue, self.data)
        with self.assertRaises(ValueError):
            approved_tag_plan(mapped, self.data, source_queue=self.queue)


if __name__ == "__main__":
    unittest.main()
