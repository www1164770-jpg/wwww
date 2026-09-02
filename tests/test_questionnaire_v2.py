import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from questionnaire_v2 import build_recommendation_profile, get_config, legacy_payload_to_answers, validate_answers
from recommend_service import rank_sites


class QuestionnaireV2Tests(unittest.TestCase):

    def test_versioned_response_storage_uses_independent_primary_key(self):
        repo_root = Path(__file__).resolve().parents[1]
        migration = (repo_root / "backend/sql/migrations/20260809_add_questionnaire_v2_responses.sql").read_text(
            encoding="utf-8"
        )
        routes = (repo_root / "backend/v1_routes.py").read_text(encoding="utf-8")

        self.assertIn("id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY", migration)
        self.assertIn("UNIQUE KEY uq_user_questionnaire_version", migration)
        self.assertIn("UNIQUE KEY uq_user_questionnaire_version", routes)
        self.assertIn("WHERE user_id=%s AND questionnaire_version=%s", routes)

    def test_developer_code_generation_follows_the_coding_branch(self):
        answers, path = validate_answers({
            "occupation": "developer",
            "developer_direction": "frontend",
            "developer_need": "code_generation",
            "coding_need": "modify_existing_code",
            "usage_frequency": "daily",
            "priority": "efficiency",
        })
        self.assertEqual(path[0], "occupation")
        self.assertIn("coding_need", path)
        self.assertEqual(answers["coding_need"], "modify_existing_code")

    def test_student_path_excludes_developer_answers(self):
        answers, path = validate_answers({
            "occupation": "student",
            "student_stage": "college",
            "student_need": "ai_learning",
            "usage_frequency": "daily",
            "priority": "easy_to_use",
            # Stale values from a previous developer path must not persist.
            "developer_direction": "frontend",
            "developer_need": "code_generation",
        })
        self.assertNotIn("developer_direction", answers)
        self.assertNotIn("developer_need", answers)
        self.assertNotIn("developer_direction", path)

    def test_profile_contains_direction_need_and_priority_tags(self):
        profile = build_recommendation_profile({
            "occupation": "developer",
            "developer_direction": "backend",
            "developer_need": "api_debugging",
            "usage_frequency": "daily",
            "priority": "professional",
        })
        self.assertEqual(profile["career_code"], "backend_developer")
        self.assertIn("api_debugging", profile["tags"])
        self.assertEqual(profile["priority"], "professional")

    def test_legacy_flat_payload_is_accepted_as_a_compatibility_path(self):
        answers, _ = validate_answers(legacy_payload_to_answers({"occupation": "frontend_developer"}))
        self.assertEqual(answers["occupation"], "developer")
        self.assertEqual(answers["developer_direction"], "frontend")

    def test_adaptive_profile_changes_site_order_for_core_need(self):
        sites = [
            {"id": "api", "name": "API 调试台", "summary": "Postman API debugging", "occupations": ["backend_developer"]},
            {"id": "ui", "name": "UI 生成器", "summary": "Figma UI interface design", "occupations": ["frontend_developer"]},
        ]
        api_first = rank_sites(sites, {"occupation": "backend_developer", "direction": "backend", "primary_need": "api_debugging", "interests": []}, limit=2)
        ui_first = rank_sites(sites, {"occupation": "frontend_developer", "direction": "frontend", "primary_need": "ui_generation", "interests": []}, limit=2)
        self.assertEqual(api_first[0]["id"], "api")
        self.assertEqual(ui_first[0]["id"], "ui")

    def test_freelancer_keeps_occupation_and_creator_options_follow_creator_type(self):
        answers, _ = validate_answers({
            "occupation": "freelancer", "freelancer_type": "writing",
            "creator_need": "proofreading", "usage_frequency": "daily", "priority": "efficiency",
        })
        profile = build_recommendation_profile(answers)
        self.assertEqual(profile["occupation"], "freelancer")
        self.assertEqual(profile["secondary_role"], "writing")
        config = get_config()
        writing_values = set(config["questions"]["creator_need"]["optionsWhen"]["creator_type"]["writing"])
        audio_values = set(config["questions"]["creator_need"]["optionsWhen"]["creator_type"]["audio"])
        self.assertIn("proofreading", writing_values)
        self.assertNotIn("proofreading", audio_values)


if __name__ == "__main__":
    unittest.main()
