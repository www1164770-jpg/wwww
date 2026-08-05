import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from occupation_utils import get_occupation_label, normalize_occupation


class OccupationUtilsTests(unittest.TestCase):
    def test_normalizes_chinese_labels(self):
        cases = {
            "前端开发": "frontend_developer",
            "后端开发": "backend_developer",
            "AI 应用开发": "ai_app_developer",
            "大模型工程师": "llm_engineer",
            "产品经理": "product_manager",
            "UI/UX 设计师": "ui_ux_designer",
            "数据分析师": "data_analyst",
            "运营": "operations",
            "技术运营": "technical_operations",
            "学生": "student",
            "教师": "teacher",
            "自媒体创作者": "creator",
            "其他": "other",
        }
        for raw_value, expected in cases.items():
            with self.subTest(raw_value=raw_value):
                self.assertEqual(normalize_occupation(raw_value), expected)

    def test_accepts_canonical_codes(self):
        for canonical in (
            "frontend_developer",
            "backend_developer",
            "ai_app_developer",
            "llm_engineer",
            "product_manager",
            "ui_ux_designer",
            "data_analyst",
            "operations",
            "technical_operations",
            "student",
            "teacher",
            "creator",
            "other",
        ):
            with self.subTest(canonical=canonical):
                self.assertEqual(normalize_occupation(canonical), canonical)

    def test_accepts_historical_codes(self):
        cases = {
            "programmer": "frontend_developer",
            "designer": "ui_ux_designer",
            "marketing": "operations",
            "ecommerce": "operations",
            "content_creator": "creator",
            "self_media_creator": "creator",
        }
        for raw_value, expected in cases.items():
            with self.subTest(raw_value=raw_value):
                self.assertEqual(normalize_occupation(raw_value), expected)

    def test_missing_and_unknown_values_do_not_become_other(self):
        for raw_value in (None, "", " ", "unknown-career"):
            with self.subTest(raw_value=raw_value):
                self.assertIsNone(normalize_occupation(raw_value))
                self.assertIsNone(get_occupation_label(raw_value))

    def test_explicit_other_maps_to_chinese_label(self):
        self.assertEqual(normalize_occupation("other"), "other")
        self.assertEqual(get_occupation_label("other"), "其他")


if __name__ == "__main__":
    unittest.main()

