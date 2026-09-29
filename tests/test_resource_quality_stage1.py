import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(1, str(ROOT))
from sqlalchemy import create_engine, text, select
from resource_quality import resource_identity, audit_resources
from resource_migration import (metadata, snapshot, approved_tag_plan, apply_plan,
    rollback, rollback_plan, maintenance_plan, claims, effective_fields, ReviewIdentityDrift)
from questionnaire_v3 import validate_answers, build_recommendation_profile
from recommend_service import rank_sites, MATCH_WEIGHTS


COMMON = {"experience_level": "intermediate", "goals": ["efficiency"],
          "priorities": ["easy_to_use"], "platforms": ["web"],
          "budget_preference": "free_first", "ai_usage_style": "daily_workflow",
          "collaboration_scenario": "small_team"}
RESEARCH = {**COMMON, "occupation": "student", "student_stage": "graduate",
    "study_field": "science", "student_tasks": ["research", "paper"],
    "student_pain_points": ["citation"], "student_need": "research", "research_need": "literature_search"}
API = {**COMMON, "occupation": "developer", "developer_direction": "backend",
    "tech_stack": ["python"], "developer_tasks": ["api"], "developer_pain_points": ["api_debugging"],
    "developer_need": "api_debugging"}


class ResourceQualityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        with self.engine.begin() as conn:
            for sql in (
                "CREATE TABLE websites(id INTEGER PRIMARY KEY, name TEXT, url TEXT, summary TEXT, description TEXT, status TEXT)",
                "CREATE TABLE tags(id INTEGER PRIMARY KEY, name TEXT UNIQUE, type TEXT)",
                "CREATE TABLE site_tags(id INTEGER PRIMARY KEY, site_id INTEGER, tag_id INTEGER)",
                "CREATE TABLE site_occupations(id INTEGER PRIMARY KEY, site_id INTEGER, occupation TEXT)",
                "CREATE TABLE favorites(id INTEGER PRIMARY KEY, site_id INTEGER, user_id INTEGER)",
                "CREATE TABLE user_behaviors(id INTEGER PRIMARY KEY, site_id INTEGER)",
                "INSERT INTO websites VALUES(1,'API Fixture','https://example.test/API','','','approved'),(2,'Literature Fixture','https://example.test/Papers','','','approved')",
                "INSERT INTO favorites VALUES(1,1,99)",
                "INSERT INTO user_behaviors VALUES(1,1)",
            ):
                conn.execute(text(sql))
            metadata.create_all(conn)
        self.queue = {"items": [{"website_id": 1, "website": "API Fixture", "url": "https://example.test/API",
            "signal": "api_debugging", "suggested_tags": ["api_debugging", "developer_tools"],
            "approved_tags": ["api_debugging"], "rejected_tags": ["developer_tools"], "review_status": "approved",
            "candidate_reason": "isolated fixture", "review_note": "Synthetic test approval, not real resource evidence",
            "review_checks": {k: True for k in ("capability_confirmed", "tag_specific", "no_profile_pollution", "evidence_clear")}}]}

    def tearDown(self):
        self.engine.dispose()

    def test_url_boundaries(self):
        self.assertEqual(resource_identity("https://EXAMPLE.test:443/API"), "https://example.test/API")
        for a, b in [("/API", "/api"), ("/a", "/b"), ("/#/a", "/#/b"),
                     ("/?a=1&a=2", "/?a=2&a=1"), ("/a//b", "/a/b"), ("/a", "/a/")]:
            self.assertNotEqual(resource_identity("https://example.test" + a), resource_identity("https://example.test" + b))

    def test_approved_subset_idempotence_and_owned_rollback(self):
        with self.engine.begin() as conn:
            plan = approved_tag_plan(self.queue, snapshot(conn))
            self.assertEqual(len(apply_plan(conn, plan)), 1)
            self.assertEqual(apply_plan(conn, approved_tag_plan(self.queue, snapshot(conn))), [])
            conn.execute(text("INSERT INTO tags(name,type) VALUES('manual_tag','general')"))
            conn.execute(text("INSERT INTO site_tags(site_id,tag_id) SELECT 1,id FROM tags WHERE name='manual_tag'"))
            self.assertEqual(len(rollback_plan(conn)), 1)
            rollback(conn)
            self.assertEqual(rollback(conn), [])
            self.assertEqual(conn.execute(text("SELECT t.name FROM tags t JOIN site_tags st ON t.id=st.tag_id")).scalars().all(), ["manual_tag"])
            self.assertEqual(conn.execute(text("SELECT site_id FROM favorites")).scalar(), 1)
            self.assertEqual(conn.execute(text("SELECT site_id FROM user_behaviors")).scalar(), 1)
            self.assertEqual(len(apply_plan(conn, approved_tag_plan(self.queue, snapshot(conn)))), 1)

    def test_review_id_drift_blocks_writes(self):
        self.queue["items"][0]["website_id"] = 999
        with self.engine.connect() as conn:
            with self.assertRaises(ReviewIdentityDrift):
                approved_tag_plan(self.queue, snapshot(conn))
            self.assertEqual(conn.execute(text("SELECT COUNT(*) FROM site_tags")).scalar(), 0)

    def test_unapproved_tag_rejected(self):
        self.queue["items"][0]["approved_tags"].append("invented_tag")
        with self.engine.connect() as conn, self.assertRaises(ValueError):
            approved_tag_plan(self.queue, snapshot(conn))

    def test_manual_priority_ai_unpublished_merge_keeps_references(self):
        base = {"kind": "field", "site_id": 1, "url": "https://example.test/API", "field": "summary", "source_ref": "fixture"}
        changes = [{**base, "value": "Human correction", "source_kind": "manual"},
                   {**base, "value": "Crawler guess", "source_kind": "web_extract"},
                   {**base, "value": "AI guess", "source_kind": "ai_suggestion"},
                   {"kind": "merge", "source_id": 1, "target_id": 2,
                    "source_url": "https://example.test/API", "target_url": "https://example.test/Papers",
                    "reviewed": True, "evidence": "Synthetic equivalence for preservation test only"}]
        with self.engine.begin() as conn:
            apply_plan(conn, maintenance_plan(changes, snapshot(conn)))
            resolved = effective_fields(conn.execute(select(claims)).mappings().all())
            self.assertEqual(resolved["summary"]["value"], "Human correction")
            self.assertEqual(conn.execute(text("SELECT COUNT(*) FROM websites")).scalar(), 2)
            self.assertEqual(conn.execute(text("SELECT site_id FROM favorites")).scalar(), 1)
            self.assertEqual(len(conn.execute(text("SELECT * FROM user_behaviors")).all()), 1)
            rollback(conn)
            self.assertEqual(effective_fields(conn.execute(select(claims)).mappings().all()), {})

    def test_distinct_needs_and_truthful_reasons(self):
        sites = [{"id": 1, "name": "API Fixture", "tags": ["api_debugging", "backend"]},
                 {"id": 2, "name": "Literature Fixture", "tags": ["literature_search", "research"]},
                 {"id": 3, "name": "Mail capital build", "reason": "Pretend perfect match", "tags": []}]
        for answers, expected in [(API, 1), (RESEARCH, 2)]:
            clean, _ = validate_answers(answers)
            profile = build_recommendation_profile(clean)
            profile["interests"] = profile["tags"]
            ranked = rank_sites(sites, profile)
            self.assertEqual(ranked[0]["id"], expected)
            self.assertTrue(ranked[0]["match_evidence"])
            fallback = next(row for row in ranked if row["id"] == 3)
            self.assertEqual(fallback["match_evidence"], [])
            self.assertIn("暂无明确", fallback["reason"])
        self.assertEqual(rank_sites(sites, {"primary_need": "api_debugging"})[-1]["need_score"], 0)
        self.assertEqual(MATCH_WEIGHTS, {"occupation": 20, "direction": 30, "primary_need": 35, "priority": 10, "other_tags": 5})

    def test_nested_answer_is_a_validation_error(self):
        for patch in ({"occupation": []}, {"tech_stack": [{}]}, {"developer_need": {}}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                validate_answers({**API, **patch})

    def test_field_overlay_never_overwrites_existing_copy_with_extraction(self):
        from resource_fields import enrich_resources
        site = {"id": 1, "summary": "Existing human copy"}
        rows = [{"id": 1, "site_id": 1, "field": "summary", "value": "Extracted copy", "source_kind": "web_extract", "source_ref": "fixture", "state": "active"}]
        self.assertEqual(enrich_resources([site], rows)[0]["summary"], "Existing human copy")


if __name__ == "__main__":
    unittest.main()
