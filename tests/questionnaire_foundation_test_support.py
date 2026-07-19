"""Shared, model-free test utilities for questionnaire foundation work."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
from typing import Any, Iterator
import unittest

from flask import Flask
from flask_jwt_extended import create_access_token
from sqlalchemy import event
from sqlalchemy.pool import StaticPool


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class FakeCursor:
    """Small DB-API cursor fake used by migration runner tests."""

    def __init__(self, connection: "FakeConnection") -> None:
        self.connection = connection
        self._one: Any = None
        self._all: list[Any] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        return None

    def execute(self, statement: str, parameters: Any = None) -> None:
        self.connection.executed.append((statement, parameters))
        if self.connection.fail_statement and self.connection.fail_statement in statement:
            raise RuntimeError("database execution failed")
        normalized = " ".join(statement.split()).upper()
        if "SELECT 1 FROM SCHEMA_MIGRATIONS" in normalized:
            self._one = (1,) if parameters[0] in self.connection.applied else None
        elif "INFORMATION_SCHEMA.TABLES" in normalized:
            self._all = [(table,) for table in self.connection.existing_tables]
        elif "INFORMATION_SCHEMA.KEY_COLUMN_USAGE" in normalized:
            target_count = (len(parameters) - 1) // 2
            excluded_tables = set(parameters[target_count:])
            self._all = [
                (table,)
                for table in self.connection.external_references
                if table not in excluded_tables
            ]
        else:
            self._one = None
            self._all = []
            if normalized.startswith("INSERT INTO SCHEMA_MIGRATIONS"):
                self.connection.applied.add(parameters[0])
            elif normalized.startswith("DELETE FROM SCHEMA_MIGRATIONS"):
                self.connection.applied.discard(parameters[0])

    def fetchone(self) -> Any:
        return self._one

    def fetchall(self) -> list[Any]:
        return self._all


class FakeConnection:
    """Context-manager compatible connection fake with observable transactions."""

    def __init__(
        self,
        *,
        applied: set[str] | None = None,
        existing_tables: tuple[str, ...] = (),
        external_references: tuple[str, ...] = (),
        fail_statement: str | None = None,
    ) -> None:
        self.applied = applied if applied is not None else set()
        self.existing_tables = existing_tables
        self.external_references = external_references
        self.fail_statement = fail_statement
        self.executed: list[tuple[str, Any]] = []
        self.commits = 0
        self.rollbacks = 0

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


def make_sqlite_app() -> Flask:
    """Create the shared SQLite app without importing questionnaire models yet."""
    from models import db

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }
    db.init_app(app)
    with app.app_context():
        @event.listens_for(db.engine, "connect")
        def enable_sqlite_foreign_keys(connection: Any, _: Any) -> None:
            connection.execute("PRAGMA foreign_keys=ON")

    return app


@contextmanager
def sqlite_session(app: Flask) -> Iterator[Any]:
    """Reserved model-free session lifecycle; ORM setup is added in Task 2."""
    from models import db

    with app.app_context():
        try:
            yield db.session
        finally:
            db.session.rollback()
            db.session.remove()


class SqlStatementCounter:
    """Count SQLAlchemy statements while active."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.count = 0

    def _after_cursor_execute(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs
        self.count += 1

    def __enter__(self) -> "SqlStatementCounter":
        event.listen(self.engine, "after_cursor_execute", self._after_cursor_execute)
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        event.remove(self.engine, "after_cursor_execute", self._after_cursor_execute)


def make_jwt_headers(app: Flask, identity: str) -> dict[str, str]:
    with app.app_context():
        return {"Authorization": f"Bearer {create_access_token(identity=identity)}"}


class QuestionnaireFoundationTestCase(unittest.TestCase):
    """Model-free base class reserved for subsequent foundation tests."""
