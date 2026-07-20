import contextlib
import io
import os
import re
import sys
import tempfile
import unittest
import gc
import warnings
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import text

from tests.questionnaire_foundation_test_support import (
    FakeConnection,
    QuestionnaireFoundationTestCase,
    make_jwt_headers,
    make_sqlite_app,
    dispose_sqlite_app,
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

MIGRATION_DIR = Path(__file__).resolve().parents[1] / "backend" / "sql" / "migrations"
EXPECTED_COLUMNS = {
    "occupations": (
        "id", "occupation_code", "name", "category", "sort_order", "enabled",
        "new_occupation_policy", "created_at", "updated_at",
    ),
    "questionnaire_definitions": (
        "id", "definition_code", "name", "description", "scope_type", "scope_key",
        "occupation_id", "user_type", "enabled", "created_by_user_id", "created_at",
        "updated_at",
    ),
    "questionnaire_versions": (
        "id", "definition_id", "version_number", "status", "current_effective_scope_key",
        "source_version_id", "version_description", "created_by_user_id",
        "published_by_user_id", "published_at", "created_at", "updated_at",
    ),
    "questionnaire_questions": (
        "id", "version_id", "question_code", "title", "description", "question_type",
        "required", "sort_order", "enabled", "is_general", "min_selections",
        "max_selections", "max_length", "created_at", "updated_at",
    ),
    "questionnaire_options": (
        "id", "question_id", "option_value", "label", "sort_order", "enabled",
        "created_at", "updated_at",
    ),
    "questionnaire_conditions": (
        "id", "version_id", "source_question_id", "target_question_id",
        "expected_option_id", "operator", "created_at", "updated_at",
    ),
}
EXPECTED_COLUMN_DEFINITIONS = {
    "occupations": (
        "id int not null auto_increment", "occupation_code varchar(64) not null",
        "name varchar(120) not null", "category varchar(120) null",
        "sort_order int not null default 0", "enabled tinyint(1) not null default 1",
        "new_occupation_policy varchar(32) not null default 'use_general'",
        "created_at datetime not null default current_timestamp",
        "updated_at datetime not null default current_timestamp on update current_timestamp",
    ),
    "questionnaire_definitions": (
        "id int not null auto_increment", "definition_code varchar(96) not null",
        "name varchar(160) not null", "description text null", "scope_type varchar(32) not null",
        "scope_key varchar(192) not null", "occupation_id int null", "user_type varchar(32) null",
        "enabled tinyint(1) not null default 1", "created_by_user_id int not null",
        "created_at datetime not null default current_timestamp",
        "updated_at datetime not null default current_timestamp on update current_timestamp",
    ),
    "questionnaire_versions": (
        "id int not null auto_increment", "definition_id int not null", "version_number int not null",
        "status varchar(32) not null default 'draft'", "current_effective_scope_key varchar(192) null",
        "source_version_id int null", "version_description text null", "created_by_user_id int not null",
        "published_by_user_id int null", "published_at datetime null",
        "created_at datetime not null default current_timestamp",
        "updated_at datetime not null default current_timestamp on update current_timestamp",
    ),
    "questionnaire_questions": (
        "id int not null auto_increment", "version_id int not null", "question_code varchar(96) not null",
        "title varchar(300) not null", "description text null", "question_type varchar(32) not null",
        "required tinyint(1) not null default 0", "sort_order int not null",
        "enabled tinyint(1) not null default 1", "is_general tinyint(1) not null default 0",
        "min_selections int null", "max_selections int null", "max_length int null",
        "created_at datetime not null default current_timestamp",
        "updated_at datetime not null default current_timestamp on update current_timestamp",
    ),
    "questionnaire_options": (
        "id int not null auto_increment", "question_id int not null", "option_value varchar(96) not null",
        "label varchar(300) not null", "sort_order int not null", "enabled tinyint(1) not null default 1",
        "created_at datetime not null default current_timestamp",
        "updated_at datetime not null default current_timestamp on update current_timestamp",
    ),
    "questionnaire_conditions": (
        "id int not null auto_increment", "version_id int not null", "source_question_id int not null",
        "target_question_id int not null", "expected_option_id int not null", "operator varchar(16) not null",
        "created_at datetime not null default current_timestamp",
        "updated_at datetime not null default current_timestamp on update current_timestamp",
    ),
}
EXPECTED_CONSTRAINT_NAMES = (
    "uq_occupations_occupation_code", "uq_occupations_name",
    "uq_questionnaire_definitions_definition_code", "uq_questionnaire_definitions_scope_key",
    "fk_questionnaire_definitions_occupation", "fk_questionnaire_definitions_created_by_user",
    "uq_questionnaire_versions_number", "uq_questionnaire_versions_current_scope",
    "fk_questionnaire_versions_definition", "fk_questionnaire_versions_source_version",
    "fk_questionnaire_versions_created_by_user", "fk_questionnaire_versions_published_by_user",
    "uq_questionnaire_questions_code", "fk_questionnaire_questions_version",
    "uq_questionnaire_options_value", "fk_questionnaire_options_question",
    "uq_questionnaire_conditions_target", "fk_questionnaire_conditions_version",
    "fk_questionnaire_conditions_source_question", "fk_questionnaire_conditions_target_question",
    "fk_questionnaire_conditions_expected_option",
)
EXPECTED_FOREIGN_KEYS = {
    ("questionnaire_definitions", "fk_questionnaire_definitions_occupation", "occupation_id", "occupations", "id", "RESTRICT"),
    ("questionnaire_definitions", "fk_questionnaire_definitions_created_by_user", "created_by_user_id", "users", "id", "RESTRICT"),
    ("questionnaire_versions", "fk_questionnaire_versions_definition", "definition_id", "questionnaire_definitions", "id", "RESTRICT"),
    ("questionnaire_versions", "fk_questionnaire_versions_source_version", "source_version_id", "questionnaire_versions", "id", "RESTRICT"),
    ("questionnaire_versions", "fk_questionnaire_versions_created_by_user", "created_by_user_id", "users", "id", "RESTRICT"),
    ("questionnaire_versions", "fk_questionnaire_versions_published_by_user", "published_by_user_id", "users", "id", "RESTRICT"),
    ("questionnaire_questions", "fk_questionnaire_questions_version", "version_id", "questionnaire_versions", "id", "RESTRICT"),
    ("questionnaire_options", "fk_questionnaire_options_question", "question_id", "questionnaire_questions", "id", "RESTRICT"),
    ("questionnaire_conditions", "fk_questionnaire_conditions_version", "version_id", "questionnaire_versions", "id", "RESTRICT"),
    ("questionnaire_conditions", "fk_questionnaire_conditions_source_question", "source_question_id", "questionnaire_questions", "id", "RESTRICT"),
    ("questionnaire_conditions", "fk_questionnaire_conditions_target_question", "target_question_id", "questionnaire_questions", "id", "RESTRICT"),
    ("questionnaire_conditions", "fk_questionnaire_conditions_expected_option", "expected_option_id", "questionnaire_options", "id", "RESTRICT"),
}
EXPECTED_UNIQUE_CONSTRAINTS = {
    ("occupations", "uq_occupations_occupation_code"),
    ("occupations", "uq_occupations_name"),
    ("questionnaire_definitions", "uq_questionnaire_definitions_definition_code"),
    ("questionnaire_definitions", "uq_questionnaire_definitions_scope_key"),
    ("questionnaire_versions", "uq_questionnaire_versions_number"),
    ("questionnaire_versions", "uq_questionnaire_versions_current_scope"),
    ("questionnaire_questions", "uq_questionnaire_questions_code"),
    ("questionnaire_options", "uq_questionnaire_options_value"),
    ("questionnaire_conditions", "uq_questionnaire_conditions_target"),
}
EXPECTED_INDEX_METADATA = {
    ("occupations", "uq_occupations_occupation_code", 0, ("occupation_code",)),
    ("occupations", "uq_occupations_name", 0, ("name",)),
    ("occupations", "idx_occupations_enabled_sort_order", 1, ("enabled", "sort_order")),
    ("questionnaire_definitions", "uq_questionnaire_definitions_definition_code", 0, ("definition_code",)),
    ("questionnaire_definitions", "uq_questionnaire_definitions_scope_key", 0, ("scope_key",)),
    ("questionnaire_definitions", "idx_questionnaire_definitions_occupation_id", 1, ("occupation_id",)),
    ("questionnaire_definitions", "idx_questionnaire_definitions_created_by_user_id", 1, ("created_by_user_id",)),
    ("questionnaire_versions", "uq_questionnaire_versions_number", 0, ("definition_id", "version_number")),
    ("questionnaire_versions", "uq_questionnaire_versions_current_scope", 0, ("current_effective_scope_key",)),
    ("questionnaire_versions", "idx_questionnaire_versions_source_version_id", 1, ("source_version_id",)),
    ("questionnaire_versions", "idx_questionnaire_versions_created_by_user_id", 1, ("created_by_user_id",)),
    ("questionnaire_versions", "idx_questionnaire_versions_published_by_user_id", 1, ("published_by_user_id",)),
    ("questionnaire_questions", "uq_questionnaire_questions_code", 0, ("version_id", "question_code")),
    ("questionnaire_questions", "idx_questionnaire_questions_version_sort_order", 1, ("version_id", "sort_order")),
    ("questionnaire_options", "uq_questionnaire_options_value", 0, ("question_id", "option_value")),
    ("questionnaire_options", "idx_questionnaire_options_question_sort_order", 1, ("question_id", "sort_order")),
    ("questionnaire_conditions", "uq_questionnaire_conditions_target", 0, ("target_question_id",)),
    ("questionnaire_conditions", "idx_questionnaire_conditions_version_id", 1, ("version_id",)),
    ("questionnaire_conditions", "idx_questionnaire_conditions_source_question_id", 1, ("source_question_id",)),
    ("questionnaire_conditions", "idx_questionnaire_conditions_expected_option_id", 1, ("expected_option_id",)),
}
TEST_DATABASE_NAME_RE = re.compile(
    r"^questionnaire(?:_(?:foundation|migration|ci|integration|metadata|local|e2e|[0-9]+))*_test(?:_[0-9]+)?$"
)


def _mysql_test_config(environ: dict[str, str]) -> dict[str, object] | None:
    """Return only a deliberately named test database configuration."""
    names = {
        "host": "QUESTIONNAIRE_TEST_DB_HOST",
        "port": "QUESTIONNAIRE_TEST_DB_PORT",
        "user": "QUESTIONNAIRE_TEST_DB_USER",
        "password": "QUESTIONNAIRE_TEST_DB_PASSWORD",
        "database": "QUESTIONNAIRE_TEST_DB_NAME",
    }
    values = {key: environ.get(name, "").strip() for key, name in names.items()}
    if not all(values.values()):
        return None
    database = values["database"].lower()
    if not TEST_DATABASE_NAME_RE.fullmatch(database):
        raise ValueError("QUESTIONNAIRE_TEST_DB_NAME must use an explicit test-only database name")
    try:
        port = int(values["port"])
    except ValueError as error:
        raise ValueError("QUESTIONNAIRE_TEST_DB_PORT must be an integer") from error
    return {**values, "port": port}


def _configured_mysql_test_database() -> dict[str, object] | None:
    try:
        return _mysql_test_config(dict(os.environ))
    except ValueError:
        return None


class FoundationMigrationSqlTests(unittest.TestCase):
    def setUp(self):
        self.up_path = MIGRATION_DIR / f"{NAME}.up.sql"
        self.down_path = MIGRATION_DIR / f"{NAME}.down.sql"

    def test_sql_files_describe_the_complete_foundation_schema(self):
        up_sql = self.up_path.read_text(encoding="utf-8")
        down_sql = self.down_path.read_text(encoding="utf-8")
        self.assertTrue(up_sql.startswith(HEADER + "\n"))
        self.assertNotIn("migration-target-tables", down_sql)

        create_order = tuple(
            re.findall(r"CREATE\s+TABLE\s+`?([a-z_]+)`?", up_sql, flags=re.IGNORECASE)
        )
        self.assertEqual(create_order, TARGETS)
        drop_order = tuple(
            re.findall(r"DROP\s+TABLE\s+`?([a-z_]+)`?", down_sql, flags=re.IGNORECASE)
        )
        self.assertEqual(drop_order, tuple(reversed(TARGETS)))

        normalized = " ".join(up_sql.split()).lower()
        for table, columns in EXPECTED_COLUMNS.items():
            with self.subTest(table=table):
                section_match = re.search(
                    rf"create table {table} \((.*?)\) engine=innodb default charset=utf8mb4;",
                    normalized,
                )
                self.assertIsNotNone(section_match)
                section = section_match.group(1) if section_match else ""
                for column in columns:
                    self.assertRegex(section, rf"`?{column}`?\s+")
                for definition in EXPECTED_COLUMN_DEFINITIONS[table]:
                    self.assertIn(definition, section)
        for token in (
            "engine=innodb", "default charset=utf8mb4", "on delete restrict",
            "uq_questionnaire_definitions_scope_key",
            "uq_questionnaire_versions_number",
            "uq_questionnaire_versions_current_scope",
            "uq_questionnaire_questions_code",
            "uq_questionnaire_options_value",
            "uq_questionnaire_conditions_target",
            "default 'use_general'", "default 'draft'", "default 0", "default 1",
        ):
            with self.subTest(token=token):
                self.assertIn(token, normalized)
        self.assertEqual(
            tuple(re.findall(r"constraint\s+([a-z_]+)", normalized)),
            EXPECTED_CONSTRAINT_NAMES,
        )
        self.assertEqual(len(re.findall(r"foreign key\s*\(", normalized)), 12)
        self.assertNotIn("create table if not exists", normalized)
        self.assertNotIn("foreign_key_checks", normalized)
        self.assertNotIn("insert into", normalized)
        self.assertNotIn("users", down_sql.lower())
        for forbidden in (
            "foreign_key_checks", "procedure", "prepare ", "execute ", "set @",
            "create table if not exists", "drop table if exists", "insert into",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, normalized)
                self.assertNotIn(forbidden, down_sql.lower())

    def test_real_sql_pair_runs_through_the_controlled_runner_fake(self):
        connection = FakeConnection()
        self.assertEqual(
            run_sql_migration.run_migration("upgrade", NAME, lambda: connection),
            "applied",
        )
        executed_up = tuple(
            sql
            for sql, _ in connection.executed
            if "CREATE TABLE" in sql and "schema_migrations" not in sql
        )
        self.assertEqual(
            tuple(re.findall(r"CREATE\s+TABLE\s+`?([a-z_]+)`?", "\n".join(executed_up), re.I)),
            TARGETS,
        )
        self.assertEqual(
            run_sql_migration.run_migration("downgrade", NAME, lambda: connection),
            "reverted",
        )
        executed_down = tuple(sql for sql, _ in connection.executed if "DROP TABLE" in sql)
        self.assertEqual(
            tuple(re.findall(r"DROP\s+TABLE\s+`?([a-z_]+)`?", "\n".join(executed_down), re.I)),
            tuple(reversed(TARGETS)),
        )


class MySqlTestConfigurationTests(unittest.TestCase):
    def test_missing_test_database_configuration_skips_integration_work(self):
        self.assertIsNone(_mysql_test_config({}))

    def test_only_explicit_questionnaire_test_database_names_are_accepted(self):
        base = {
            "QUESTIONNAIRE_TEST_DB_HOST": "127.0.0.1",
            "QUESTIONNAIRE_TEST_DB_PORT": "3306",
            "QUESTIONNAIRE_TEST_DB_USER": "questionnaire_test",
            "QUESTIONNAIRE_TEST_DB_PASSWORD": "not-a-real-password",
        }
        for database in (
            "questionnaire_test",
            "questionnaire_foundation_test",
            "questionnaire_migration_test_20260719",
        ):
            with self.subTest(database=database):
                configured = {**base, "QUESTIONNAIRE_TEST_DB_NAME": database}
                self.assertEqual(_mysql_test_config(configured)["database"], database)

        for database in (
            "", "nav_site", "nav_site_prod", "production", "production_backup",
            "questionnaire_foundation", "questionnaire_prod_test", "test_questionnaire",
        ):
            with self.subTest(database=database):
                configured = {**base, "QUESTIONNAIRE_TEST_DB_NAME": database}
                if not database:
                    self.assertIsNone(_mysql_test_config(configured))
                else:
                    with self.assertRaisesRegex(ValueError, "test-only database name"):
                        _mysql_test_config(configured)


@unittest.skipUnless(
    _configured_mysql_test_database(),
    "QUESTIONNAIRE_TEST_DB_HOST/PORT/USER/PASSWORD/NAME are not safely configured",
)
class MySqlFoundationMigrationIntegrationTests(unittest.TestCase):
    """Runs only against a deliberately configured test-only MySQL database."""

    @classmethod
    def setUpClass(cls):
        import pymysql

        cls.config = _configured_mysql_test_database()
        assert cls.config is not None
        cls.pymysql = pymysql
        cls.connection = pymysql.connect(
            host=cls.config["host"],
            port=cls.config["port"],
            user=cls.config["user"],
            password=cls.config["password"],
            database=cls.config["database"],
            charset="utf8mb4",
            autocommit=False,
        )
        with cls.connection.cursor() as cursor:
            cursor.execute("SELECT DATABASE()")
            connected_database = cursor.fetchone()[0]
        if connected_database != cls.config["database"]:
            cls.connection.close()
            raise RuntimeError("refusing to run migration tests against an unexpected database")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "connection"):
            cls.connection.close()

    @contextmanager
    def connection_factory(self):
        try:
            yield self.connection
        finally:
            pass

    def _execute(self, statement: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(statement)
        self.connection.commit()

    def _table_names(self) -> set[str]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT TABLE_NAME FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN (" +
                ",".join(["%s"] * len(TARGETS)) + ")",
                TARGETS,
            )
            return {row[0] for row in cursor.fetchall()}

    def _migration_is_recorded(self) -> bool:
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
                ("schema_migrations",),
            )
            if cursor.fetchone() is None:
                return False
            cursor.execute("SELECT 1 FROM schema_migrations WHERE name = %s", (NAME,))
            return cursor.fetchone() is not None

    def _remove_test_schema(self) -> None:
        if not self._migration_is_recorded():
            return
        run_sql_migration.run_migration("downgrade", NAME, self.connection_factory)

    def setUp(self):
        self._remove_test_schema()
        self._execute("DROP TABLE IF EXISTS questionnaire_migration_external_reference")
        self._execute("DROP TABLE IF EXISTS questionnaire_migration_legacy_guard")

    def tearDown(self):
        self._execute("DROP TABLE IF EXISTS questionnaire_migration_external_reference")
        self._remove_test_schema()
        self._execute("DROP TABLE IF EXISTS questionnaire_migration_legacy_guard")

    def test_upgrade_schema_and_safe_downgrade_behaviour(self):
        self._execute(
            "CREATE TABLE questionnaire_migration_legacy_guard "
            "(id INT NOT NULL PRIMARY KEY) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        )
        self.assertEqual(
            run_sql_migration.run_migration("upgrade", NAME, self.connection_factory),
            "applied",
        )
        self.assertEqual(self._table_names(), set(TARGETS))
        self.assertTrue(self._migration_is_recorded())
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT TABLE_NAME, ENGINE, TABLE_COLLATION FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN (" +
                ",".join(["%s"] * len(TARGETS)) + ")",
                TARGETS,
            )
            table_rows = cursor.fetchall()
            self.assertEqual(
                {row[0] for row in table_rows},
                set(TARGETS),
            )
            self.assertTrue(all(row[1].upper() == "INNODB" for row in table_rows))
            self.assertTrue(all(row[2].lower().startswith("utf8mb4_") for row in table_rows))
            cursor.execute(
                "SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN (" +
                ",".join(["%s"] * len(TARGETS)) + ")",
                TARGETS,
            )
            columns_by_table = {table: set() for table in TARGETS}
            for table, column in cursor.fetchall():
                columns_by_table[table].add(column)
            self.assertEqual(columns_by_table, {table: set(columns) for table, columns in EXPECTED_COLUMNS.items()})
            cursor.execute(
                "SELECT k.TABLE_NAME, k.CONSTRAINT_NAME, k.ORDINAL_POSITION, k.COLUMN_NAME, "
                "k.REFERENCED_TABLE_NAME, k.REFERENCED_COLUMN_NAME, r.DELETE_RULE "
                "FROM information_schema.KEY_COLUMN_USAGE AS k "
                "INNER JOIN information_schema.REFERENTIAL_CONSTRAINTS AS r "
                "ON r.CONSTRAINT_SCHEMA = k.CONSTRAINT_SCHEMA "
                "AND r.TABLE_NAME = k.TABLE_NAME "
                "AND r.CONSTRAINT_NAME = k.CONSTRAINT_NAME "
                "WHERE k.CONSTRAINT_SCHEMA = DATABASE() "
                "AND k.TABLE_NAME IN (" +
                ",".join(["%s"] * len(TARGETS)) + ") "
                "AND k.REFERENCED_TABLE_NAME IS NOT NULL",
                TARGETS,
            )
            foreign_keys = set()
            for table, constraint, position, column, referenced_table, referenced_column, delete_rule in cursor.fetchall():
                self.assertEqual(position, 1)
                foreign_keys.add(
                    (table, constraint, column, referenced_table, referenced_column, delete_rule)
                )
            self.assertEqual(foreign_keys, EXPECTED_FOREIGN_KEYS)
            cursor.execute(
                "SELECT TABLE_NAME, CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS "
                "WHERE TABLE_SCHEMA = DATABASE() AND CONSTRAINT_TYPE = 'UNIQUE' "
                "AND TABLE_NAME IN (" + ",".join(["%s"] * len(TARGETS)) + ")",
                TARGETS,
            )
            unique_constraints = {(row[0], row[1]) for row in cursor.fetchall()}
            self.assertEqual(unique_constraints, EXPECTED_UNIQUE_CONSTRAINTS)
            cursor.execute(
                "SELECT TABLE_NAME, INDEX_NAME, NON_UNIQUE, SEQ_IN_INDEX, COLUMN_NAME "
                "FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN (" +
                ",".join(["%s"] * len(TARGETS)) + ") "
                "AND (INDEX_NAME LIKE 'uq_%' OR INDEX_NAME LIKE 'idx_%') "
                "ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX",
                TARGETS,
            )
            index_columns: dict[tuple[str, str, int], list[tuple[int, str]]] = {}
            for table, index, non_unique, position, column in cursor.fetchall():
                index_columns.setdefault((table, index, non_unique), []).append((position, column))
            indexes = {
                (table, index, non_unique, tuple(column for _, column in sorted(columns)))
                for (table, index, non_unique), columns in index_columns.items()
            }
            self.assertEqual(indexes, EXPECTED_INDEX_METADATA)
            cursor.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", ("questionnaire_migration_legacy_guard",))
            self.assertIsNotNone(cursor.fetchone())
        self._execute(
            "CREATE TABLE questionnaire_migration_external_reference ("
            "id INT NOT NULL PRIMARY KEY, question_id INT NOT NULL, "
            "CONSTRAINT fk_questionnaire_migration_external_question "
            "FOREIGN KEY (question_id) REFERENCES questionnaire_questions(id) ON DELETE RESTRICT"
            ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        )
        with self.assertRaisesRegex(RuntimeError, "external foreign key references"):
            run_sql_migration.run_migration("downgrade", NAME, self.connection_factory)
        self.assertEqual(self._table_names(), set(TARGETS))
        self.assertTrue(self._migration_is_recorded())
        self._execute("DROP TABLE questionnaire_migration_external_reference")
        self.assertEqual(
            run_sql_migration.run_migration("downgrade", NAME, self.connection_factory),
            "reverted",
        )
        self.assertEqual(self._table_names(), set())
        self.assertFalse(self._migration_is_recorded())
        self._execute(
            "CREATE TABLE occupations (id INT NOT NULL PRIMARY KEY) "
            "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
        )
        with self.assertRaisesRegex(RuntimeError, "partial migration state"):
            run_sql_migration.run_migration("upgrade", NAME, self.connection_factory)
        self.assertFalse(self._migration_is_recorded())
        self._execute("DROP TABLE occupations")


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

    def test_execution_failure_rolls_back_before_connection_context_exits(self):
        self.write_migration()
        connection = FakeConnection(
            fail_statement="CREATE TABLE occupations", close_on_exit=True
        )
        with self.assertRaisesRegex(RuntimeError, "migration execution failed") as error:
            run_sql_migration.run_migration("upgrade", NAME, lambda: connection)
        self.assertEqual(connection.rollbacks, 1)
        self.assertTrue(connection.closed)
        self.assertEqual(connection.rollback_after_close_attempts, 0)
        self.assertNotIn("password", str(error.exception))

    def test_rollback_failure_does_not_leak_sensitive_connection_details(self):
        self.write_migration()
        connection = FakeConnection(
            fail_statement="CREATE TABLE occupations",
            rollback_error=RuntimeError("mysql://user:password@host/rollback"),
        )
        with self.assertRaisesRegex(RuntimeError, "migration execution failed") as error:
            run_sql_migration.run_migration("upgrade", NAME, lambda: connection)
        self.assertEqual(connection.rollback_attempts, 1)
        self.assertNotIn("password", str(error.exception))
        self.assertNotIn("mysql://", str(error.exception))

    def test_safety_rejection_rolls_back_before_connection_context_exits(self):
        self.write_migration()
        connection = FakeConnection(
            existing_tables=("occupations",), close_on_exit=True
        )
        with self.assertRaisesRegex(RuntimeError, "partial migration state") as error:
            run_sql_migration.run_migration("upgrade", NAME, lambda: connection)
        self.assertEqual(connection.rollbacks, 1)
        self.assertTrue(connection.closed)
        self.assertEqual(connection.rollback_after_close_attempts, 0)
        self.assertNotIn("password", str(error.exception))

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

    def test_cross_schema_same_named_table_blocks_downgrade(self):
        self.write_migration()
        self.factory_connection.applied.add(NAME)
        self.factory_connection.external_references = (("other_database", "questionnaire_versions"),)
        with self.assertRaisesRegex(RuntimeError, "external foreign key references"):
            run_sql_migration.run_migration("downgrade", NAME, self.factory)
        self.assertIn(NAME, self.factory_connection.applied)
        self.assertEqual(self.factory_connection.rollbacks, 1)
        self.assertFalse(any("DROP TABLE occupations" in sql for sql, _ in self.factory_connection.executed))

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
    def test_dispose_sqlite_app_closes_open_sqlite_connections(self):
        from models import db
        app = make_sqlite_app()
        with app.app_context():
            db.session.execute(text("PRAGMA foreign_keys")).scalar_one()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            dispose_sqlite_app(app)
            del app
            gc.collect()
        self.assertFalse(any("unclosed database" in str(item.message) for item in caught))
    def test_foundation_base_test_case_is_a_unittest_test_case(self):
        self.assertTrue(issubclass(QuestionnaireFoundationTestCase, unittest.TestCase))

    def test_sqlite_factory_initializes_jwt_for_model_free_headers(self):
        app = make_sqlite_app()
        try:
            headers = make_jwt_headers(app, "questionnaire-admin")
            self.assertTrue(headers["Authorization"].startswith("Bearer "))
        finally:
            dispose_sqlite_app(app)

    def test_sqlite_factory_uses_static_pool_and_enables_foreign_keys(self):
        app = make_sqlite_app()
        try:
            self.assertEqual(app.config["SQLALCHEMY_DATABASE_URI"], "sqlite://")
            with app.app_context():
                from models import db
                self.assertEqual(db.session.execute(text("PRAGMA foreign_keys")).scalar_one(), 1)
        finally:
            dispose_sqlite_app(app)


if __name__ == "__main__":
    unittest.main()
