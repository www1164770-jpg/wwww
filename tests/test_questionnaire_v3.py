import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from questionnaire_v3 import (  # noqa: E402
    QUESTIONNAIRE_VERSION, answer_path, build_recommendation_profile, get_config,
    validate_answers, v2_defaults,
)
from recommend_service import MATCH_WEIGHTS
from recommend_service import rank_sites


COMMON = {
    "experience_level": "intermediate", "goals": ["efficiency"],
    "priorities": ["easy_to_use", "free_value"], "platforms": ["windows", "web"],
    "budget_preference": "free_first", "ai_usage_style": "daily_workflow",
    "collaboration_scenario": "small_team",
}


class QuestionnaireV3Tests(unittest.TestCase):
    def complete(self, answers):
        result, path = validate_answers({**answers, **COMMON})
        self.assertEqual(result, {key: result[key] for key in path})
        self.assertLessEqual(len(path), 15)
        return result, path

    def test_developer_frontend_vue_code_generation_path(self):
        answers, path = self.complete({
            "occupation": "developer", "developer_direction": "frontend", "tech_stack": ["vue", "typescript"],
            "developer_tasks": ["new_features"], "developer_pain_points": ["slow_coding"],
            "developer_need": "code_generation", "coding_need": "generate_from_requirement",
        })
        self.assertIn("coding_need", path)
        profile = build_recommendation_profile(answers)
        self.assertEqual(profile["profile_schema_version"], 3)
        self.assertEqual(profile["direction"], "frontend")
        self.assertEqual(profile["primary_need"], "code_generation")
        self.assertEqual(profile["priority"], "easy_to_use")

    def test_developer_backend_api_debugging_path(self):
        answers, _ = self.complete({
            "occupation": "developer", "developer_direction": "backend", "tech_stack": ["python"],
            "developer_tasks": ["api"], "developer_pain_points": ["api_debugging"], "developer_need": "api_debugging",
        })
        self.assertEqual(build_recommendation_profile(answers)["career_code"], "backend_engineer")

    def test_student_college_computer_science_programming_path(self):
        _, path = self.complete({
            "occupation": "student", "student_stage": "college", "study_field": "computer_science",
            "student_tasks": ["programming"], "student_pain_points": ["understanding"], "student_need": "programming",
            "research_need": "writing",
        })
        self.assertIn("study_field", path)

    def test_student_graduate_research_paper_path(self):
        answers, _ = self.complete({
            "occupation": "student", "student_stage": "graduate", "study_field": "science",
            "student_tasks": ["research", "paper"], "student_pain_points": ["citation"], "student_need": "research",
            "research_need": "literature_search",
        })
        self.assertIn("citation", build_recommendation_profile(answers)["pain_points"])

    def test_creator_type_filters_video_options(self):
        config = get_config()
        values = set(config["questions"]["creator_tasks"]["optionsWhen"]["creator_type"]["writing"])
        self.assertNotIn("editing", values)
        answers, _ = self.complete({
            "occupation": "creator", "creator_type": "writing", "content_platforms": ["zhihu"],
            "creator_tasks": ["copywriting"], "creator_need": "copywriting",
        })
        self.assertNotIn("editing", answers["creator_tasks"])

    def test_designer_ui_ux_prototype_path(self):
        answers, _ = self.complete({
            "occupation": "designer", "designer_direction": "ui_ux", "designer_outputs": ["ui"],
            "designer_stage": ["prototype"], "designer_pain_points": ["prototype"], "designer_need": "prototype",
        })
        profile = build_recommendation_profile(answers)
        self.assertEqual(profile["direction"], "ui_ux")
        self.assertIn("prototype", profile["tasks"])

    def test_creator_short_video_includes_video_options(self):
        config = get_config()
        values = set(config["questions"]["creator_tasks"]["optionsWhen"]["creator_type"]["short_video"])
        self.assertTrue({"editing", "subtitle", "ai_video"}.issubset(values))

    def test_teacher_office_product_and_freelancer_paths(self):
        cases = [
            {"occupation": "teacher", "teaching_stage": "college", "teacher_subject": "computer", "teacher_tasks": ["lesson_plan"], "teacher_need": "lesson_plan"},
            {"occupation": "office", "office_role": "finance", "office_tasks": ["automation"], "office_automation_need": ["excel"], "office_need": "automation"},
            {"occupation": "product_operation", "product_role": "product_manager", "product_tasks": ["prototype"], "product_need": "prototype"},
            {"occupation": "freelancer", "freelancer_secondary_role": "development", "developer_direction": "backend", "tech_stack": ["python"], "developer_tasks": ["api"], "developer_pain_points": ["api_debugging"], "developer_need": "api_debugging", "freelancer_business_needs": ["quotation"]},
        ]
        for case in cases:
            with self.subTest(case=case["occupation"]):
                answers, _ = self.complete(case)
                profile = build_recommendation_profile(answers)
                self.assertEqual(profile["occupation"], case["occupation"])

    def test_multi_limit_and_stale_answers_are_rejected_or_removed(self):
        with self.assertRaisesRegex(ValueError, "too many selections"):
            validate_answers({**COMMON, "occupation": "other", "general_scenario": "learning", "general_need": "learning", "goals": ["efficiency", "learning", "automation", "research"]})
        answers, path = self.complete({"occupation": "other", "general_scenario": "learning", "general_need": "learning", "developer_direction": "frontend"})
        self.assertNotIn("developer_direction", answers)
        self.assertNotIn("developer_direction", path)

    def test_v2_defaults_are_editable_and_priority_is_migrated(self):
        defaults = v2_defaults({"occupation": "developer", "developer_direction": "frontend", "priority": "ai"})
        self.assertEqual(defaults["priorities"], ["ai"])
        self.assertEqual(QUESTIONNAIRE_VERSION, 3)

    def test_new_users_receive_v3_and_v3_profile_still_drives_recommendation(self):
        self.assertEqual(get_config()["version"], 3)
        answers, _ = self.complete({
            "occupation": "developer", "developer_direction": "backend", "tech_stack": ["python"],
            "developer_tasks": ["api"], "developer_pain_points": ["api_debugging"], "developer_need": "api_debugging",
        })
        profile = build_recommendation_profile(answers)
        ranked = rank_sites([
            {"id": "api", "name": "API tool", "summary": "Postman API debugging", "occupations": ["backend_developer"]},
            {"id": "design", "name": "Design tool", "summary": "Figma prototype", "occupations": ["ui_ux_designer"]},
        ], {"occupation": profile["career_code"], "direction": profile["direction"], "primary_need": profile["primary_need"], "priority": profile["priority"], "interests": profile["tags"]}, limit=2)
        self.assertEqual(ranked[0]["id"], "api")

    def test_phase_one_weights_remain_unchanged(self):
        self.assertEqual(MATCH_WEIGHTS, {"occupation": 20, "direction": 30, "primary_need": 35, "priority": 10, "other_tags": 5})

    def test_observation_context_keeps_profile_schema_separate_from_algorithm(self):
        repo_root = Path(__file__).resolve().parents[1]
        routes = (repo_root / "backend" / "v1_routes.py").read_text(encoding="utf-8")
        tracker = (repo_root / "backend" / "frontend" / "src" / "utils" / "behaviorTracker.js").read_text(encoding="utf-8")
        coverage = (repo_root / "backend" / "scripts" / "analyze_questionnaire_v3_signal_coverage.py").read_text(encoding="utf-8")
        self.assertIn("profile_schema_version", routes)
        self.assertIn("profile_schema_version", tracker)
        self.assertIn('"algorithm_version": "phase1-v1"', coverage)


if __name__ == "__main__":
    unittest.main()
