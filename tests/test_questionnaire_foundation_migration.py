import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import text

from tests.questionnaire_foundation_test_support import (
    FakeConnection,
    QuestionnaireFoundationTestCase,
    make_sqlite_app,
)

from backend.scripts import run_sql_migration


TARGETS = (
    "occupations",
    "questionnaire_definitions",
    "questionnaire_versions",
    "questionnaire_questions",
    "questionnaire_options",
    "questionnaire_conditions",
)
HEADER = "-- migration-target-tables: " + ",".join(TARGETS)
NAME = "20260719_questionnaire_foundation"


class MigrationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.migrations = Path(self.temp_dir.name)
        self.factory_connection = FakeConnection()
        self.factory = lambda: self.factory_connection
        self.directory_patch = patch.object(run_sql_migration, "MIGRATIONS_DIR", self.migrations)
        self.directory_patch.start()
        self.addCleanup(self.directory_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

    def write_migration(self, *, up=None, down="DROP TABLE occupations;"):
        (self.migrations / f"{NAME}.up.sql").write_text(
            up if up is not None else f"{HEADER}\nCREATE TABLE occupations (id INT);",
            encoding="utf-8",
        )
        (self.migrations / f"{NAME}.down.sql").write_text(down, encoding="utf-8")

    def test_migration_name_only_accepts_date_underscore_and_safe_lowercase_slug(self):
        self.write_migration()
        self.assertEqual(
            run_sql_migration.migration_paths(NAME)[0],
            (self.migrations / f"{NAME}.up.sql").resolve(),
        )
        for bad_name in ("20260719bad", "2026071_questionnaire", "20260719_Upper", "20260719_../escape", "C:/escape"):
            with self.assertRaisesRegex(ValueError, "invalid migration name"):
                run_sql_migration.migration_paths(bad_name)

    def test_missing_migration_file_is_rejected(self):
        with self.assertRaisesRegex(FileNotFoundError, "migration SQL file is missing"):
            run_sql_migration.run_migration("upgrade", NAME, self.factory)

    def test_target_declaration_accepts_the_exact_six_tables_in_stable_order(self):
        self.assertEqual(run_sql_migration.parse_target_tables(HEADER), TARGETS)

    def test_target_declaration_must_be_the_exact_first_line_and_fixed_table_order(self):
        invalid = (
            "\n" + HEADER,
            "-- a normal comment\n" + HEADER,
            "-- migration-target-tables: questionnaire_definitions,occupations,questionnaire_versions,questionnaire_questions,questionnaire_options,questionnaire_conditions",
            "-- migration-target-tables: occupations,questionnaire_definitions,questionnaire_versions,questionnaire_questions,questionnaire_options",
        )
        for declaration in invalid:
            with self.subTest(declaration=declaration):
                with self.assertRaisesRegex(ValueError, "target table declaration"):
                    run_sql_migration.parse_target_tables(declaration)

    def test_target_declaration_rejects_missing_empty_duplicate_and_unsafe_names(self):
        invalid = (
            "SELECT 1",
            "-- migration-target-tables: ",
            "-- migration-target-tables: occupations,occupations",
            "-- migration-target-tables: app.occupations",
            "-- migration-target-tables: `occupations`",
            "-- migration-target-tables: occupations;DROP TABLE users",
            "-- migration-target-tables: ../occupations",
            "-- migration-target-tables: CONCAT('occupation', 's')",
        )
        for declaration in invalid:
            with self.subTest(declaration=declaration):
                with self.assertRaisesRegex(ValueError, "target table declaration"):
                    run_sql_migration.parse_target_tables(declaration)

    def test_upgrade_returns_already_applied_without_reexecuting_sql(self):
        self.write_migration()
        self.factory_connection.applied.add(NAME)
        self.assertEqual(run_sql_migration.run_migration("upgrade", NAME, self.factory), "already_applied")
        self.assertFalse(any("CREATE TABLE occupations" in sql for sql, _ in self.factory_connection.executed))

    def test_downgrade_returns_not_applied_without_reexecuting_sql(self):
        self.write_migration()
        self.assertEqual(run_sql_migration.run_migration("downgrade", NAME, self.factory), "not_applied")
        self.assertFalse(any("DROP TABLE occupations" in sql for sql, _ in self.factory_connection.executed))

    def test_upgrade_records_only_after_sql_succeeds_and_downgrade_deletes_only_after_sql_succeeds(self):
        self.write_migration()
        self.assertEqual(run_sql_migration.run_migration("upgrade", NAME, self.factory), "applied")
        self.assertIn(NAME, self.factory_connection.applied)
        self.assertEqual(run_sql_migration.run_migration("downgrade", NAME, self.factory), "reverted")
        self.assertNotIn(NAME, self.factory_connection.applied)

    def test_execution_failure_rolls_back_and_raises_a_safe_error(self):
        self.write_migration()
        self.factory_connection.fail_statement = "CREATE TABLE occupations"
        with self.assertRaisesRegex(RuntimeError, "migration execution failed") as error:
            run_sql_migration.run_migration("upgrade", NAME, self.factory)
        self.assertEqual(self.factory_connection.rollbacks, 1)
        self.assertNotIn("database execution failed", str(error.exception))

    def test_connection_factory_failure_is_converted_to_a_safe_error_without_rollback(self):
        self.write_migration()

        def unavailable_connection():
            raise RuntimeError("mysql://user:password@host/foundation")

        with self.assertRaisesRegex(RuntimeError, "migration execution failed") as error:
            run_sql_migration.run_migration("upgrade", NAME, unavailable_connection)
        self.assertNotIn("password", str(error.exception))
        self.assertNotIn("mysql://", str(error.exception))

    def test_unregistered_existing_target_table_is_rejected_as_partial_state(self):
        self.write_migration()
        self.factory_connection.existing_tables = ("occupations",)
        with self.assertRaisesRegex(RuntimeError, "partial migration state"):
            run_sql_migration.run_migration("upgrade", NAME, self.factory)
        self.assertNotIn(NAME, self.factory_connection.applied)

    def test_external_references_block_downgrade_but_internal_target_references_do_not(self):
        self.write_migration()
        self.factory_connection.applied.add(NAME)
        self.factory_connection.external_references = ("unrelated_answers",)
        with self.assertRaisesRegex(RuntimeError, "external foreign key references"):
            run_sql_migration.run_migration("downgrade", NAME, self.factory)
        self.factory_connection.external_references = ("questionnaire_versions",)
        self.assertEqual(run_sql_migration.run_migration("downgrade", NAME, self.factory), "reverted")
        external_sql, external_params = next(
            (sql, params)
            for sql, params in self.factory_connection.executed
            if "INFORMATION_SCHEMA.KEY_COLUMN_USAGE" in sql
        )
        self.assertIn("REFERENCED_TABLE_SCHEMA = DATABASE()", external_sql)
        self.assertIn("schema_migrations", external_params)

    def test_invalid_direction_is_rejected(self):
        self.write_migration()
        with self.assertRaisesRegex(ValueError, "invalid migration direction"):
            run_sql_migration.run_migration("sideways", NAME, self.factory)


class MigrationCliTests(unittest.TestCase):
    def test_importing_module_does_not_execute_a_migration(self):
        self.assertTrue(callable(run_sql_migration.main))

    def test_main_rejects_missing_extra_direction_and_name_arguments(self):
        for argv in ([], ["upgrade"], ["upgrade", NAME, "extra"], ["sideways", NAME], ["upgrade", "bad"]):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                self.assertNotEqual(run_sql_migration.main(argv), 0)

    def test_main_returns_zero_for_a_patched_production_connection_factory(self):
        with tempfile.TemporaryDirectory() as path:
            migrations = Path(path)
            (migrations / f"{NAME}.up.sql").write_text(f"{HEADER}\nSELECT 1;", encoding="utf-8")
            (migrations / f"{NAME}.down.sql").write_text("SELECT 1;", encoding="utf-8")
            connection = FakeConnection()
            with patch.object(run_sql_migration, "MIGRATIONS_DIR", migrations), patch.object(
                run_sql_migration, "get_production_connection", return_value=connection
            ) as connection_factory, contextlib.redirect_stdout(output := io.StringIO()):
                self.assertEqual(run_sql_migration.main(["upgrade", NAME]), 0)
            connection_factory.assert_called_once_with()
            self.assertEqual(output.getvalue(), f"{NAME} applied\n")

    def test_main_returns_nonzero_and_does_not_leak_connection_or_sql_details(self):
        stream = io.StringIO()
        with patch.object(run_sql_migration, "get_production_connection", side_effect=RuntimeError("mysql://user:password@host")), contextlib.redirect_stderr(stream):
            self.assertNotEqual(run_sql_migration.main(["upgrade", NAME]), 0)
        self.assertNotIn("password", stream.getvalue())
        self.assertNotIn("mysql://", stream.getvalue())


class ModelFreeSupportTests(unittest.TestCase):
    def test_foundation_base_test_case_is_a_unittest_test_case(self):
        self.assertTrue(issubclass(QuestionnaireFoundationTestCase, unittest.TestCase))

    def test_sqlite_factory_uses_static_pool_and_enables_foreign_keys(self):
        app = make_sqlite_app()
        self.assertEqual(app.config["SQLALCHEMY_DATABASE_URI"], "sqlite://")
        self.assertEqual(
            app.config["SQLALCHEMY_ENGINE_OPTIONS"]["connect_args"],
            {"check_same_thread": False},
        )
        with app.app_context():
            from models import db

            self.assertEqual(db.session.execute(text("PRAGMA foreign_keys")).scalar_one(), 1)


if __name__ == "__main__":
    unittest.main()
