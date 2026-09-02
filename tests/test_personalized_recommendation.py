import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from recommend_service import rank_sites


class PersonalizedRecommendationTests(unittest.TestCase):
    sites = [
        {
            "id": "figma",
            "name": "Figma",
            "tags": ["developer", "frontend", "ui_generation", "prototype"],
            "occupations": [],
        },
        {
            "id": "postman",
            "name": "Postman",
            "tags": ["developer", "backend", "api", "api_debugging", "testing"],
            "occupations": [],
            "is_free": 1,
        },
        {
            "id": "cursor",
            "name": "Cursor",
            "tags": ["developer", "ai_ml", "ai", "ai_coding", "code_generation"],
            "occupations": [],
        },
    ]

    def test_same_occupation_different_needs_change_top_result(self):
        frontend = rank_sites(
            self.sites,
            {
                "occupation": "developer",
                "direction": "frontend",
                "primary_need": "ui_generation",
                "priority": "efficiency",
            },
            limit=3,
        )
        backend = rank_sites(
            self.sites,
            {
                "occupation": "developer",
                "direction": "backend",
                "primary_need": "api_debugging",
                "priority": "free_value",
            },
            limit=3,
        )
        ai = rank_sites(
            self.sites,
            {
                "occupation": "developer",
                "direction": "ai_ml",
                "primary_need": "code_generation",
                "priority": "ai",
            },
            limit=3,
        )

        self.assertEqual(frontend[0]["id"], "figma")
        self.assertEqual(backend[0]["id"], "postman")
        self.assertEqual(ai[0]["id"], "cursor")
        self.assertTrue(frontend[0]["match_reasons"])
        self.assertIn("match_score", backend[0])

    def test_rotation_pool_is_deterministic_and_unique(self):
        profile = {"occupation": "developer", "direction": "backend", "primary_need": "api_debugging"}
        first = rank_sites(self.sites, profile, limit=3)
        second = rank_sites(self.sites, profile, limit=3)
        self.assertEqual([item["id"] for item in first], [item["id"] for item in second])
        self.assertEqual(len({item["id"] for item in first}), len(first))

    def test_nullable_catalog_metrics_do_not_break_ranking(self):
        sites = [
            {"id": "null", "name": "Null metrics", "quality_score": None, "tags": ["backend"]},
            {"id": "number", "name": "Number metrics", "quality_score": 90, "tags": ["backend"]},
        ]
        ranked = rank_sites(
            sites,
            {"occupation": "developer", "direction": "backend", "primary_need": "api_debugging"},
            limit=2,
        )
        self.assertEqual(len(ranked), 2)

    def test_student_ai_learning_profile_keeps_real_candidates(self):
        sites = [
            {"id": "course", "name": "AI Course", "tags": ["learning", "ai"]},
            {"id": "notes", "name": "Knowledge Notes", "tags": ["learning", "efficiency"]},
        ]
        ranked = rank_sites(
            sites,
            {
                "occupation": "student",
                "primary_need": "ai_learning",
                "priority": "ai",
                "interests": ["learning", "college", "ai_learning", "ai"],
            },
            limit=60,
        )
        self.assertEqual([item["id"] for item in ranked], ["course", "notes"])
        self.assertGreater(ranked[0]["match_score"], 0)


if __name__ == "__main__":
    unittest.main()
