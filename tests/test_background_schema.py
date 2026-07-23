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

        self.assertTrue(
            sql.startswith("-- migration-target-tables: user_backgrounds,user_background_settings\n")
        )
        self.assertIn("CREATE TABLE user_backgrounds", sql)
        self.assertIn("CREATE TABLE user_background_settings", sql)
        self.assertEqual(sql.count("ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"), 2)
        self.assertEqual(sql.count("user_id INT NOT NULL"), 2)
        self.assertIn("status ENUM('active', 'deleted') NOT NULL DEFAULT 'active'", sql)
        self.assertIn(
            "page_type ENUM('global', 'home', 'category', 'favorites', 'ai_assistant', 'profile') NOT NULL",
            sql,
        )
        self.assertIn("UNIQUE KEY uq_user_background_settings_page (user_id, page_type)", sql)
        self.assertIn("UNIQUE KEY uq_user_backgrounds_storage_path (storage_path)", sql)
        self.assertIn("KEY idx_user_backgrounds_user_status_created (user_id, status, created_at)", sql)
        self.assertIn("KEY idx_user_background_settings_background (background_id)", sql)
        self.assertIn("FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE", sql)
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

        normalized_statements = tuple(
            statement.strip() + ";" for statement in sql.split(";") if statement.strip()
        )
        self.assertEqual(
            normalized_statements,
            ("DROP TABLE user_background_settings;", "DROP TABLE user_backgrounds;"),
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
            {foreign_key.ondelete for foreign_key in setting_columns.user_id.foreign_keys},
            {"CASCADE"},
        )
        self.assertEqual(
            {foreign_key.ondelete for foreign_key in setting_columns.background_id.foreign_keys},
            {"SET NULL"},
        )
        self.assertEqual(
            {foreign_key.target_fullname for foreign_key in setting_columns.background_id.foreign_keys},
            {"user_backgrounds.id"},
        )
        self.assertEqual(background_columns.status.type.enums, ["active", "deleted"])
        self.assertEqual(
            setting_columns.page_type.type.enums,
            ["global", "home", "category", "favorites", "ai_assistant", "profile"],
        )
        self.assertEqual(setting_columns.size_mode.type.enums, ["cover", "contain", "auto"])
        for column in (
            background_columns.user_id,
            background_columns.storage_path,
            background_columns.original_name,
            background_columns.mime_type,
            background_columns.file_size,
            background_columns.width,
            background_columns.height,
            background_columns.status,
            setting_columns.user_id,
            setting_columns.page_type,
            setting_columns.overlay_opacity,
            setting_columns.blur_px,
            setting_columns.position_x,
            setting_columns.position_y,
            setting_columns.size_mode,
        ):
            with self.subTest(nullable=column.name):
                self.assertFalse(column.nullable)
        for column in (
            background_columns.id,
            background_columns.file_size,
            background_columns.width,
            background_columns.height,
            setting_columns.id,
            setting_columns.background_id,
            setting_columns.blur_px,
            setting_columns.position_x,
            setting_columns.position_y,
        ):
            with self.subTest(column=column.name):
                self.assertTrue(getattr(column.type, "unsigned", False))
        self.assertEqual(
            {constraint.name: str(constraint.sqltext) for constraint in UserBackground.__table__.constraints
             if constraint.__class__.__name__ == "CheckConstraint"},
            {
                "chk_user_backgrounds_size": "file_size > 0 AND file_size <= 10485760",
                "chk_user_backgrounds_dimensions": "width > 0 AND height > 0",
            },
        )
        self.assertEqual(
            {constraint.name: str(constraint.sqltext) for constraint in UserBackgroundSetting.__table__.constraints
             if constraint.__class__.__name__ == "CheckConstraint"},
            {
                "chk_user_background_settings_overlay": "overlay_opacity >= 0.00 AND overlay_opacity <= 0.70",
                "chk_user_background_settings_blur": "blur_px <= 20",
                "chk_user_background_settings_x": "position_x <= 100",
                "chk_user_background_settings_y": "position_y <= 100",
            },
        )
        self.assertEqual(
            {constraint.name for constraint in UserBackground.__table__.constraints
             if constraint.__class__.__name__ == "UniqueConstraint"},
            {"uq_user_backgrounds_storage_path"},
        )
        self.assertEqual(
            {index.name: tuple(column.name for column in index.columns) for index in UserBackground.__table__.indexes},
            {"idx_user_backgrounds_user_status_created": ("user_id", "status", "created_at")},
        )
        self.assertEqual(
            {index.name: tuple(column.name for column in index.columns) for index in UserBackgroundSetting.__table__.indexes},
            {"idx_user_background_settings_background": ("background_id",)},
        )
        self.assertEqual(
            {constraint.name for constraint in UserBackgroundSetting.__table__.constraints
             if constraint.__class__.__name__ == "UniqueConstraint"},
            {"uq_user_background_settings_page"},
        )
        for table in (UserBackground.__table__, UserBackgroundSetting.__table__):
            with self.subTest(table=table.name):
                options = table.dialect_options["mysql"]
                self.assertEqual(options["engine"], "InnoDB")
                self.assertEqual(options["charset"], "utf8mb4")
                self.assertEqual(options["collate"], "utf8mb4_unicode_ci")
        expected_server_defaults = {
            "mime_type": "'image/webp'",
            "status": "'active'",
            "created_at": "CURRENT_TIMESTAMP",
            "updated_at": "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        }
        for column_name, expected in expected_server_defaults.items():
            with self.subTest(column=column_name):
                self.assertEqual(str(background_columns[column_name].server_default.arg), expected)
        for column_name, expected in {
            "overlay_opacity": "0.36",
            "blur_px": "0",
            "position_x": "50",
            "position_y": "50",
            "size_mode": "'cover'",
            "created_at": "CURRENT_TIMESTAMP",
            "updated_at": "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        }.items():
            with self.subTest(column=column_name):
                self.assertEqual(str(setting_columns[column_name].server_default.arg), expected)
        self.assertTrue(setting_columns.background_id.nullable)


if __name__ == "__main__":
    unittest.main()
