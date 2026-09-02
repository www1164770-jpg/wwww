import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from career_catalog import BY_CATEGORY, CAREERS
from career_recommend_service import CAREER_MATCH_WEIGHTS, build_career_recommendations
from occupation_utils import normalize_occupation


class CareerCatalogRecommendationTests(unittest.TestCase):
    def recommend(self, **profile):
        return build_career_recommendations(profile, limit=8)

    def codes(self, **profile):
        return [item["career_code"] for item in self.recommend(**profile)]

    def test_catalog_is_broad_and_each_record_has_required_fields(self):
        self.assertGreaterEqual(len(CAREERS), 70)
        self.assertEqual(len(BY_CATEGORY), 8)
        required = {"code", "name", "category", "description", "occupation", "directions", "strong_tags", "supporting_tags", "tasks", "pain_points"}
        self.assertTrue(all(required <= set(item) for item in CAREERS))

    def test_ai_llm_profile_prioritizes_llm_application_engineer(self):
        rows = self.recommend(
            profile_schema_version=3, occupation="developer", direction="ai_ml", primary_need="code_generation",
            skills=["python", "pytorch", "tensorflow", "llm"], tasks=["api", "deployment", "data_processing"],
            pain_points=["slow_coding", "hard_debugging"], goals=["ai_ml"],
        )
        self.assertEqual(rows[0]["career_code"], "llm_application_engineer")
        self.assertEqual(rows[0]["match_level"], "very_high")
        self.assertLessEqual(len(rows[0]["match_reasons"]), 2)

    def test_framework_specialization_needs_framework_evidence(self):
        base = dict(profile_schema_version=3, occupation="developer", direction="frontend", primary_need="ui_generation", tasks=["new_features"])
        vue_codes = self.codes(**base, skills=["vue", "typescript"])
        react_codes = self.codes(**base, skills=["react", "typescript"])
        generic_rows = self.recommend(**base, skills=["typescript"])
        generic_scores = {item["career_code"]: item["score"] for item in generic_rows}
        self.assertLess(vue_codes.index("vue_engineer"), vue_codes.index("react_engineer"))
        self.assertLess(react_codes.index("react_engineer"), react_codes.index("vue_engineer"))
        self.assertLessEqual(generic_scores.get("vue_engineer", 0), 50)
        self.assertLessEqual(generic_scores.get("react_engineer", 0), 50)

    def test_backend_api_and_devops_profiles_have_distinct_specialties(self):
        backend = self.codes(profile_schema_version=3, occupation="developer", direction="backend", primary_need="api_debugging", skills=["python"], tasks=["api", "database"], pain_points=["api_debugging"])
        devops = self.codes(profile_schema_version=3, occupation="developer", direction="devops", primary_need="deployment", skills=["docker", "kubernetes", "python"], tasks=["deployment"], pain_points=["deployment"])
        self.assertIn("api_engineer", backend[:4])
        self.assertIn("python_engineer", backend[:4])
        self.assertIn("devops_engineer", devops[:3])

    def test_non_technical_personas_and_v2_fallbacks_work(self):
        self.assertIn("graduate_student", self.codes(profile_schema_version=3, occupation="student", direction="graduate", primary_need="research", skills=["science"], tasks=["research", "paper"], pain_points=["find_resources"]))
        self.assertEqual(self.codes(profile_schema_version=3, occupation="creator", direction="short_video", primary_need="editing", skills=[], tasks=["video", "editing"], pain_points=[])[0], "short_video_creator")
        self.assertIn("ui_ux_designer", self.codes(profile_schema_version=3, occupation="designer", direction="ui_ux", primary_need="prototype", skills=[], tasks=["prototype"], pain_points=[]))
        self.assertIn("finance", self.codes(profile_schema_version=3, occupation="office", direction="finance", primary_need="spreadsheets", skills=[], tasks=["spreadsheets"], pain_points=[]))
        self.assertIn("backend_engineer", self.codes(profile_schema_version=2, career_code="backend_developer", interests=["api", "python"], tags=["api", "python"]))

    def test_scores_have_no_fixed_twenty_percent_floor_and_legacy_codes_resolve(self):
        self.assertEqual(CAREER_MATCH_WEIGHTS, {"occupation": 15, "direction": 25, "primary_need": 20, "skills": 20, "tasks": 10, "pain_points": 5, "goals": 5})
        self.assertEqual(self.recommend(profile_schema_version=3, occupation="other", direction="", primary_need="", skills=[], tasks=[], pain_points=[], goals=[]), [])
        self.assertEqual(normalize_occupation("frontend_developer"), "frontend_engineer")
        self.assertEqual(normalize_occupation("ai_app_developer"), "ai_application_engineer")


if __name__ == "__main__":
    unittest.main()
