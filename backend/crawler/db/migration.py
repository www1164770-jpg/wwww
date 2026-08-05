"""Forward-only migration runner guarded to the crawler database boundary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


INITIAL_MIGRATION_VERSION = "0001_initial"
MIGRATION_DIR = Path(__file__).resolve().parent / "migrations"


class MigrationSafetyError(ValueError):
    """Raised before a migration can target an unsafe database."""


@dataclass(frozen=True, slots=True)
class MigrationResult:
    database_name: str
    applied_versions: tuple[str, ...]
    skipped_versions: tuple[str, ...]


class _EngineLike(Protocol):
    def begin(self): ...


def validate_migration_target(database_url: str) -> str:
    """Return a safe database name without including credentials in errors."""

    try:
        url = make_url(database_url)
    except (ArgumentError, TypeError, ValueError) as error:
        raise MigrationSafetyError(
            "Crawler migration refused: invalid independent database URL"
        ) from error
    if url.get_backend_name() != "mysql":
        raise MigrationSafetyError(
            "Crawler migration refused: target must use MySQL"
        )
    database_name = (url.database or "").strip()
    if not database_name:
        raise MigrationSafetyError(
            "Crawler migration refused: database name is required"
        )
    if database_name not in {"zhihui_crawler", "zhihui_crawler_test"}:
        raise MigrationSafetyError(
            "Crawler migration refused: target is not an approved crawler database"
        )
    return database_name


def _migration_statements(path: Path) -> tuple[str, ...]:
    lines = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("--")
    ]
    statements = tuple(
        statement.strip()
        for statement in "\n".join(lines).split(";")
        if statement.strip()
    )
    forbidden = re.compile(r"^\s*(DROP|TRUNCATE|DELETE)\b", re.IGNORECASE)
    for statement in statements:
        normalized = statement.lstrip().upper()
        if forbidden.search(statement) or "NAV_SITE" in normalized:
            raise MigrationSafetyError("Crawler migration contains a forbidden operation")
        if not normalized.startswith(("CREATE TABLE", "CREATE INDEX", "ALTER TABLE")):
            raise MigrationSafetyError("Crawler migration contains an unsupported operation")
    return statements


def run_migrations(engine: _EngineLike, database_url: str) -> MigrationResult:
    """Apply each known migration once; never perform downgrade operations."""

    database_name = validate_migration_target(database_url)
    engine_url = getattr(engine, "url", None)
    if engine_url is None:
        raise MigrationSafetyError(
            "Crawler migration refused: engine target cannot be verified"
        )
    try:
        parsed_engine_url = make_url(engine_url)
    except (ArgumentError, TypeError, ValueError) as error:
        raise MigrationSafetyError(
            "Crawler migration refused: engine target cannot be verified"
        ) from error
    engine_database_name = (parsed_engine_url.database or "").strip()
    if (
        parsed_engine_url.get_backend_name() != "mysql"
        or engine_database_name != database_name
    ):
        raise MigrationSafetyError(
            "Crawler migration refused: engine and configured targets differ"
        )
    migration_paths = tuple(sorted(MIGRATION_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")))
    if not migration_paths:
        raise MigrationSafetyError("Crawler migration files are unavailable")
    applied: list[str] = []
    skipped: list[str] = []

    with engine.begin() as connection:
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS crawler_schema_migrations (
                version VARCHAR(128) NOT NULL PRIMARY KEY,
                applied_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """.strip()
        )
        for migration_path in migration_paths:
            version = migration_path.stem
            existing = connection.execute(
                text(
                    "SELECT version FROM crawler_schema_migrations "
                    "WHERE version = :version"
                ),
                {"version": version},
            ).scalar_one_or_none()
            if existing is not None:
                skipped.append(version)
                continue
            for statement in _migration_statements(migration_path):
                connection.exec_driver_sql(statement)
            connection.execute(
                text(
                    "INSERT INTO crawler_schema_migrations (version) "
                    "VALUES (:version)"
                ),
                {"version": version},
            )
            applied.append(version)

    return MigrationResult(
        database_name=database_name,
        applied_versions=tuple(applied),
        skipped_versions=tuple(skipped),
    )
