import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from career_recommend_service import (
    build_career_recommendations,
    filter_sites_for_career,
)


OCCUPATIONS = [
    "frontend_developer",
    "backend_developer",
    "ai_app_developer",
    "product_manager",
    "ui_ux_designer",
    "data_analyst",
    "creator",
]

TAG_MAP = {
    "frontend_developer": ["programming", "AI tools", "project_development"],
    "backend_developer": ["programming", "API", "database"],
    "ai_app_developer": ["AI tools", "programming", "project_development"],
    "product_manager": ["product management", "startup resources", "data analysis"],
    "ui_ux_designer": ["design resources", "assets", "AI tools"],
    "data_analyst": ["data analysis", "programming", "AI tools"],
    "creator": ["content_creation", "assets", "AI tools"],
}


class DynamicCareerRecommendationTests(unittest.TestCase):
    def test_different_questionnaires_change_top_career(self):
        engineering = build_career_recommendations(
            {
                "occupation": "backend_developer",
                "skill_level": "senior",
                "interests": ["programming", "data analysis"],
                "purposes": ["project_development"],
                "preferences": ["professional first"],
            },
            OCCUPATIONS,
            TAG_MAP,
        )
        design = build_career_recommendations(
            {
                "occupation": "ui_ux_designer",
                "skill_level": "beginner",
                "interests": ["design resources", "assets"],
                "purposes": ["design_assets"],
                "preferences": ["tutorial first"],
            },
            OCCUPATIONS,
            TAG_MAP,
        )

        self.assertNotEqual(engineering[0]["code"], design[0]["code"])
        self.assertNotEqual(engineering[0]["reason"], design[0]["reason"])

    def test_recommendation_contains_match_reason_and_user_tags(self):
        recommendations = build_career_recommendations(
            {
                "occupation": "frontend_developer",
                "skill_level": "intermediate",
                "interests": ["programming", "AI tools"],
                "purposes": ["project_development"],
                "preferences": [],
            },
            OCCUPATIONS,
            TAG_MAP,
        )

        first = recommendations[0]
        self.assertEqual(first["code"], "frontend_developer")
        self.assertGreater(first["match_score"], 0)
        self.assertTrue(first["reason"])
        self.assertTrue(first["ability_tags"])
        self.assertTrue(first["interest_tags"])

    def test_sites_are_filtered_by_career_before_ranking(self):
        sites = [
            {
                "id": "mdn",
                "name": "MDN Web Docs",
                "occupations": ["frontend_developer"],
                "summary": "JavaScript API documentation",
            },
            {
                "id": "kaggle",
                "name": "Kaggle",
                "occupations": ["data_analyst"],
                "summary": "Data science datasets",
            },
            {
                "id": "social",
                "name": "Social Network",
                "occupations": [],
                "summary": "General popular website",
            },
        ]

        frontend_sites = filter_sites_for_career(
            sites, "frontend_developer", ["javascript"]
        )
        data_sites = filter_sites_for_career(
            sites, "data_analyst", ["data", "analytics"]
        )

        self.assertEqual([site["id"] for site in frontend_sites], ["mdn"])
        self.assertEqual([site["id"] for site in data_sites], ["kaggle"])
        self.assertNotEqual(frontend_sites, data_sites)


if __name__ == "__main__":
    unittest.main()
