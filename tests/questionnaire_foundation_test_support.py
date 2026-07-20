"""Shared, model-free test utilities for questionnaire foundation work."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
from typing import Any, Iterator
import unittest

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
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
            self._all = []
            for reference in self.connection.external_references:
                schema, table = (
                    reference if isinstance(reference, tuple) else ("current_database", reference)
                )
                if schema == "current_database" and table in excluded_tables:
                    continue
                self._all.append((schema, table))
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
        external_references: tuple[str | tuple[str, str], ...] = (),
        fail_statement: str | None = None,
        close_on_exit: bool = False,
        rollback_error: Exception | None = None,
    ) -> None:
        self.applied = applied if applied is not None else set()
        self.existing_tables = existing_tables
        self.external_references = external_references
        self.fail_statement = fail_statement
        self.close_on_exit = close_on_exit
        self.rollback_error = rollback_error
        self.closed = False
        self.rollback_after_close_attempts = 0
        self.rollback_attempts = 0
        self.executed: list[tuple[str, Any]] = []
        self.commits = 0
        self.rollbacks = 0

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.close_on_exit:
            self.closed = True
        return None

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollback_attempts += 1
        if self.closed:
            self.rollback_after_close_attempts += 1
            raise RuntimeError("rollback on closed mysql://user:password@host")
        if self.rollback_error is not None:
            raise self.rollback_error
        self.rollbacks += 1


def make_sqlite_app() -> Flask:
    """Create the shared SQLite app used by foundation model tests."""
    from models import db
    import questionnaire_models  # noqa: F401  Register models on the shared metadata.

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["JWT_SECRET_KEY"] = "questionnaire-foundation-test-jwt-secret"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "poolclass": StaticPool,
        "connect_args": {"check_same_thread": False},
    }
    db.init_app(app)
    JWTManager(app)
    with app.app_context():
        engine = db.engine

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(connection: Any, _: Any) -> None:
            connection.execute("PRAGMA foreign_keys=ON")

    return app


@contextmanager
def sqlite_session(app: Flask) -> Iterator[Any]:
    """Provide an isolated SQLite ORM session for one foundation test."""
    from models import db

    with app.app_context():
        db.create_all()
        try:
            yield db.session
        finally:
            db.session.rollback()
            db.session.remove()
            db.drop_all()
            db.engine.dispose()


def add_occupation(session: Any, **fields: Any) -> Any:
    """Persist one occupation after its Task 2 model is registered."""
    from questionnaire_models import Occupation

    occupation = Occupation(**fields)
    session.add(occupation)
    session.flush()
    return occupation


def add_definition(session: Any, **fields: Any) -> Any:
    """Persist one definition after its Task 3 model is registered."""
    from questionnaire_models import QuestionnaireDefinition

    definition = QuestionnaireDefinition(**fields)
    session.add(definition)
    session.flush()
    return definition


def add_version(session: Any, **fields: Any) -> Any:
    """Persist one version after its Task 3 model is registered."""
    from questionnaire_models import QuestionnaireVersion

    version = QuestionnaireVersion(**fields)
    session.add(version)
    session.flush()
    return version


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
