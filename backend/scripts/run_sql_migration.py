"""Controlled runner for named SQL upgrade and downgrade migration pairs."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Callable, Sequence


MIGRATION_NAME_RE = re.compile(r"^[0-9]{8}_[a-z0-9_]+$")
TARGET_TABLES = (
    "occupations",
    "questionnaire_definitions",
    "questionnaire_versions",
    "questionnaire_questions",
    "questionnaire_options",
    "questionnaire_conditions",
)
TARGET_HEADER = "-- migration-target-tables: " + ",".join(TARGET_TABLES)
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "sql" / "migrations"


class MigrationSafetyError(RuntimeError):
    """A safe, actionable refusal before a destructive migration action."""


def get_production_connection():
    """Create the normal application MySQL connection, never a test connection."""
    backend_dir = Path(__file__).resolve().parents[1]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from db_pool import get_connection

    return get_connection()


def migration_paths(name: str) -> tuple[Path, Path]:
    """Return the fixed-directory SQL pair for a validated migration name."""
    if not MIGRATION_NAME_RE.fullmatch(name):
        raise ValueError("invalid migration name")
    directory = Path(MIGRATIONS_DIR).resolve()
    up_path = (directory / f"{name}.up.sql").resolve()
    down_path = (directory / f"{name}.down.sql").resolve()
    if up_path.parent != directory or down_path.parent != directory:
        raise ValueError("invalid migration path")
    return up_path, down_path


def parse_target_tables(up_sql: str) -> tuple[str, ...]:
    """Require the fixed, first-line declaration for the foundation table set."""
    first_line = up_sql.splitlines()[0] if up_sql.splitlines() else ""
    if first_line != TARGET_HEADER:
        raise ValueError("target table declaration must be the exact first line")
    return TARGET_TABLES


def _row_value(row, key: str):
    if isinstance(row, dict):
        return row[key]
    return row[0]


def _split_sql_statements(sql: str) -> tuple[str, ...]:
    """Split simple migration SQL without interpreting semicolons in quoted strings."""
    lines = [line for line in sql.splitlines() if not line.lstrip().startswith("--")]
    text = "\n".join(lines)
    statements: list[str] = []
    current: list[str] = []
    quote: str | None = None
    escaped = False
    for character in text:
        current.append(character)
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
        elif character in ("'", '"', "`"):
            quote = character
        elif character == ";":
            statement = "".join(current[:-1]).strip()
            if statement:
                statements.append(statement)
            current = []
    trailing = "".join(current).strip()
    if trailing:
        statements.append(trailing)
    return tuple(statements)


def _ensure_schema_migrations(cursor) -> None:
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "name VARCHAR(128) NOT NULL PRIMARY KEY, "
        "applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )


def _is_applied(cursor, name: str) -> bool:
    cursor.execute("SELECT 1 FROM schema_migrations WHERE name = %s", (name,))
    return cursor.fetchone() is not None


def _existing_target_tables(cursor, target_tables: tuple[str, ...]) -> tuple[str, ...]:
    placeholders = ", ".join("%s" for _ in target_tables)
    cursor.execute(
        "SELECT TABLE_NAME FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN (" + placeholders + ")",
        target_tables,
    )
    return tuple(_row_value(row, "TABLE_NAME") for row in cursor.fetchall())


def _external_references(cursor, target_tables: tuple[str, ...]) -> tuple[str, ...]:
    referenced_placeholders = ", ".join("%s" for _ in target_tables)
    excluded_tables = ("schema_migrations", *target_tables)
    excluded_placeholders = ", ".join("%s" for _ in excluded_tables)
    cursor.execute(
        "SELECT DISTINCT TABLE_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
        "WHERE REFERENCED_TABLE_SCHEMA = DATABASE() "
        "AND REFERENCED_TABLE_NAME IN (" + referenced_placeholders + ") "
        "AND TABLE_NAME NOT IN (" + excluded_placeholders + ")",
        (*target_tables, *excluded_tables),
    )
    return tuple(_row_value(row, "TABLE_NAME") for row in cursor.fetchall())


def _execute_sql(cursor, sql: str) -> None:
    for statement in _split_sql_statements(sql):
        cursor.execute(statement)


def run_migration(
    direction: str,
    name: str,
    connection_factory: Callable[[], object],
) -> str:
    """Apply or revert one migration and return its resulting state."""
    if direction not in {"upgrade", "downgrade"}:
        raise ValueError("invalid migration direction")
    up_path, down_path = migration_paths(name)
    if not up_path.is_file() or not down_path.is_file():
        raise FileNotFoundError("migration SQL file is missing")
    up_sql = up_path.read_text(encoding="utf-8")
    down_sql = down_path.read_text(encoding="utf-8")
    target_tables = parse_target_tables(up_sql)

    with connection_factory() as connection:
        try:
            with connection.cursor() as cursor:
                _ensure_schema_migrations(cursor)
                applied = _is_applied(cursor, name)
                if direction == "upgrade":
                    if applied:
                        return "already_applied"
                    if _existing_target_tables(cursor, target_tables):
                        raise MigrationSafetyError("partial migration state detected")
                    _execute_sql(cursor, up_sql)
                    cursor.execute(
                        "INSERT INTO schema_migrations (name) VALUES (%s)", (name,)
                    )
                    connection.commit()
                    return "applied"

                if not applied:
                    return "not_applied"
                if _external_references(cursor, target_tables):
                    raise MigrationSafetyError("external foreign key references block downgrade")
                _execute_sql(cursor, down_sql)
                cursor.execute("DELETE FROM schema_migrations WHERE name = %s", (name,))
                connection.commit()
                return "reverted"
        except (ValueError, FileNotFoundError):
            raise
        except MigrationSafetyError:
            connection.rollback()
            raise
        except Exception:
            connection.rollback()
            raise RuntimeError("migration execution failed") from None


def main(argv: Sequence[str] | None = None) -> int:
    """Run `upgrade NAME` or `downgrade NAME` from the command line."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2:
        print("usage: run_sql_migration.py <upgrade|downgrade> <migration_name>", file=sys.stderr)
        return 2
    direction, name = arguments
    try:
        result = run_migration(direction, name, get_production_connection)
    except Exception:
        print("migration failed", file=sys.stderr)
        return 1
    print(f"{name} {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
