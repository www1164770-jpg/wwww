from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_DIR = ROOT / "backend" / "sql" / "migrations"
UP_PATH = MIGRATION_DIR / "20260723_user_backgrounds.up.sql"
DOWN_PATH = MIGRATION_DIR / "20260723_user_backgrounds.down.sql"


class BackgroundSchemaTests(unittest.TestCase):
    def test_migration_defines_approved_background_tables_and_constraints(self):
        self.assertTrue(UP_PATH.exists(), f"missing migration: {UP_PATH.name}")
        sql = UP_PATH.read_text(encoding="utf-8")

        self.assertIn("CREATE TABLE user_backgrounds", sql)
        self.assertIn("CREATE TABLE user_background_settings", sql)
        self.assertIn("status ENUM('active', 'deleted') NOT NULL DEFAULT 'active'", sql)
        self.assertIn(
            "page_type ENUM('global', 'home', 'category', 'favorites', 'ai_assistant', 'profile') NOT NULL",
            sql,
        )
        self.assertIn("UNIQUE KEY uq_user_background_settings_page (user_id, page_type)", sql)
        self.assertIn("ON DELETE SET NULL", sql)
        for constraint in (
            "chk_user_backgrounds_size",
            "chk_user_backgrounds_dimensions",
            "chk_user_background_settings_overlay",
            "chk_user_background_settings_blur",
            "chk_user_background_settings_x",
            "chk_user_background_settings_y",
        ):
            with self.subTest(constraint=constraint):
                self.assertIn(constraint, sql)

    def test_downgrade_drops_child_table_before_parent_table(self):
        self.assertTrue(DOWN_PATH.exists(), f"missing migration: {DOWN_PATH.name}")
        sql = DOWN_PATH.read_text(encoding="utf-8")

        self.assertLess(
            sql.index("DROP TABLE user_background_settings;"),
            sql.index("DROP TABLE user_backgrounds;"),
        )

    def test_sqlalchemy_models_expose_schema_fields_and_foreign_keys(self):
        import backend.models as models

        self.assertTrue(hasattr(models, "UserBackground"))
        self.assertTrue(hasattr(models, "UserBackgroundSetting"))
        UserBackground = models.UserBackground
        UserBackgroundSetting = models.UserBackgroundSetting

        background_columns = UserBackground.__table__.c
        setting_columns = UserBackgroundSetting.__table__.c
        self.assertIn("storage_path", background_columns)
        self.assertIn("background_id", setting_columns)
        self.assertIn("overlay_opacity", setting_columns)
        self.assertEqual(
            {foreign_key.ondelete for foreign_key in background_columns.user_id.foreign_keys},
            {"CASCADE"},
        )
        self.assertEqual(
            {foreign_key.ondelete for foreign_key in setting_columns.background_id.foreign_keys},
            {"SET NULL"},
        )
        self.assertEqual(setting_columns.overlay_opacity.default.arg, 0.36)


if __name__ == "__main__":
    unittest.main()
