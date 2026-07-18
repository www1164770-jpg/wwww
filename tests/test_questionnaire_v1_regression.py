import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"


class QuestionnaireV1RegressionTests(unittest.TestCase):
    def test_focused_migration_contains_only_the_four_user_fields(self):
        migration = (
            BACKEND_DIR
            / "sql"
            / "migrations"
            / "20260714_add_user_questionnaire_fields.sql"
        ).read_text(encoding="utf-8")

        for field in (
            "questionnaire_completed",
            "has_survey",
            "user_tags",
            "interests",
        ):
            self.assertIn(field, migration)
        self.assertNotIn("DROP ", migration.upper())
        self.assertNotIn("DELETE ", migration.upper())
        self.assertNotIn("UPDATE ", migration.upper())

    def test_questionnaire_submit_rolls_back_when_second_write_fails(self):
        route_source = (BACKEND_DIR / "v1_routes.py").read_text(encoding="utf-8")

        self.assertIn("except Exception:", route_source)
        self.assertIn("conn.rollback()", route_source)

    def test_unexpected_error_logs_the_returned_error_id(self):
        handler_source = (BACKEND_DIR / "app_extensions.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("error_id = datetime.now().strftime", handler_source)
        self.assertIn("error_id={error_id}", handler_source)


if __name__ == "__main__":
    unittest.main()
