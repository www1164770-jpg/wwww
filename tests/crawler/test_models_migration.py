from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import unittest

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from backend.crawler.db import CrawlerBase, CrawlTask
from backend.crawler.db.migration import (
    INITIAL_MIGRATION_VERSION,
    MigrationSafetyError,
    run_migrations,
    validate_migration_target,
)
from backend.crawler.db.session import create_crawler_engine, session_scope
from backend.crawler.config import CrawlerConfigError, CrawlerSettings
from tests.crawler.support import NOW, make_sqlite_engine, sqlite_session


class CrawlerModelTests(unittest.TestCase):
    def test_independent_metadata_contains_phase_one_through_phase_three_tables(self) -> None:
        self.assertEqual(
            set(CrawlerBase.metadata.tables),
            {
                "crawl_runs",
                "crawl_tasks",
                "worker_heartbeats",
                "crawler_settings",
                "outbox_events",
                "fetch_results",
                "discovered_links",
                "analysis_results",
                "risk_decisions",
                "icon_assets",
                "review_cases",
                "review_events",
                "publish_records",
                "publish_previews",
            },
        )

    def test_sqlite_schema_has_required_unique_constraints_and_indexes(self) -> None:
        engine = make_sqlite_engine()
        try:
            inspector = inspect(engine)
            task_unique = {
                tuple(item["column_names"])
                for item in inspector.get_unique_constraints("crawl_tasks")
            }
            task_indexes = {
                item["name"]: tuple(item["column_names"])
                for item in inspector.get_indexes("crawl_tasks")
            }

            self.assertIn(("task_uid",), task_unique)
            self.assertIn(("task_type", "active_dedupe_key"), task_unique)
            self.assertEqual(
                task_indexes["ix_crawl_tasks_lease_candidates"],
                ("status", "available_at", "priority", "created_at"),
            )
            self.assertEqual(
                task_indexes["ix_crawl_tasks_expired_leases"],
                ("status", "leased_until"),
            )
        finally:
            CrawlerBase.metadata.drop_all(engine)
            engine.dispose()

    def test_database_enforces_active_task_dedupe_but_allows_terminal_history(
        self,
    ) -> None:
        common = {
            "task_type": "fetch_url",
            "target": "https://example.com/",
            "target_hash": "a" * 64,
            "dedupe_key": "b" * 64,
            "priority": 100,
            "status": "pending",
            "attempt_count": 0,
            "max_attempts": 3,
            "available_at": NOW,
            "created_at": NOW,
            "updated_at": NOW,
        }
        with sqlite_session() as session:
            session.add(
                CrawlTask(
                    task_uid="task-active-1",
                    active_dedupe_key="b" * 64,
                    **common,
                )
            )
            session.flush()
            with session.begin_nested():
                session.add(
                    CrawlTask(
                        task_uid="task-active-2",
                        active_dedupe_key="b" * 64,
                        **common,
                    )
                )
                with self.assertRaises(IntegrityError):
                    session.flush()

            terminal_common = {
                **common,
                "status": "completed",
                "active_dedupe_key": None,
                "completed_at": NOW,
            }
            session.add_all(
                [
                    CrawlTask(task_uid="task-history-1", **terminal_common),
                    CrawlTask(task_uid="task-history-2", **terminal_common),
                ]
            )
            session.flush()

    def test_crawler_engine_requires_only_crawler_database_setting(self) -> None:
        settings = CrawlerSettings.from_env({})

        with self.assertRaisesRegex(CrawlerConfigError, "CRAWLER_DATABASE_URL"):
            create_crawler_engine(settings)

        for unsafe_url in (
            "mysql+pymysql://user:secret@localhost/nav_site",
            "mysql+pymysql://user:secret@localhost/other_test",
            "sqlite:///crawler.sqlite3",
        ):
            with self.subTest(unsafe_url=unsafe_url):
                unsafe = CrawlerSettings.from_env({"CRAWLER_DATABASE_URL": unsafe_url})
                with self.assertRaises(CrawlerConfigError):
                    create_crawler_engine(unsafe)

    def test_session_scope_commits_success_and_rolls_back_failures(self) -> None:
        engine = make_sqlite_engine()
        factory = __import__(
            "backend.crawler.db.session",
            fromlist=["create_session_factory"],
        ).create_session_factory(engine)
        try:
            with session_scope(factory) as session:
                session.add(
                    CrawlTask(
                        task_uid="committed-task",
                        task_type="smoke",
                        target="target",
                        target_hash="a" * 64,
                        dedupe_key="b" * 64,
                        active_dedupe_key="b" * 64,
                        priority=100,
                        status="pending",
                        attempt_count=0,
                        max_attempts=3,
                        available_at=NOW,
                        created_at=NOW,
                        updated_at=NOW,
                    )
                )

            with factory() as verification:
                self.assertIsNotNone(
                    verification.query(CrawlTask)
                    .filter_by(task_uid="committed-task")
                    .one_or_none()
                )

            with self.assertRaisesRegex(RuntimeError, "rollback marker"):
                with session_scope(factory) as session:
                    session.add(
                        CrawlTask(
                            task_uid="rolled-back-task",
                            task_type="smoke",
                            target="other",
                            target_hash="c" * 64,
                            dedupe_key="d" * 64,
                            active_dedupe_key="d" * 64,
                            priority=100,
                            status="pending",
                            attempt_count=0,
                            max_attempts=3,
                            available_at=NOW,
                            created_at=NOW,
                            updated_at=NOW,
                        )
                    )
                    session.flush()
                    raise RuntimeError("rollback marker")

            with factory() as verification:
                self.assertIsNone(
                    verification.query(CrawlTask)
                    .filter_by(task_uid="rolled-back-task")
                    .one_or_none()
                )
        finally:
            CrawlerBase.metadata.drop_all(engine)
            engine.dispose()


@dataclass
class _ScalarResult:
    value: object

    def scalar_one_or_none(self):
        return self.value


class _RecordingConnection:
    def __init__(self) -> None:
        self.applied: set[str] = set()
        self.driver_sql: list[str] = []
        self.parameters: list[dict[str, str] | None] = []

    def exec_driver_sql(self, statement: str):
        self.driver_sql.append(statement)

    def execute(self, statement, parameters=None):
        sql = str(statement)
        self.parameters.append(parameters)
        if sql.lstrip().upper().startswith("SELECT VERSION"):
            version = parameters["version"]
            return _ScalarResult(version if version in self.applied else None)
        if sql.lstrip().upper().startswith("INSERT INTO"):
            self.applied.add(parameters["version"])
        return _ScalarResult(None)


class _RecordingEngine:
    def __init__(
        self,
        url: str = "mysql+pymysql://user:secret@localhost/zhihui_crawler_test",
    ) -> None:
        self.url = url
        self.connection = _RecordingConnection()

    @contextmanager
    def begin(self):
        yield self.connection


class MigrationSafetyTests(unittest.TestCase):
    def test_migration_allows_only_the_two_exact_crawler_databases(self) -> None:
        self.assertEqual(
            validate_migration_target(
                "mysql+pymysql://user:secret@localhost/zhihui_crawler"
            ),
            "zhihui_crawler",
        )
        self.assertEqual(
            validate_migration_target(
                "mysql+pymysql://user:secret@localhost/zhihui_crawler_test"
            ),
            "zhihui_crawler_test",
        )

    def test_migration_refuses_formal_missing_and_non_mysql_targets(self) -> None:
        for url in (
            "mysql+pymysql://user:secret@localhost/nav_site",
            "mysql+pymysql://user:secret@localhost/contest_production",
            "mysql+pymysql://user:secret@localhost",
            "sqlite:///crawler_test.db",
        ):
            with self.subTest(url=url):
                with self.assertRaises(MigrationSafetyError) as caught:
                    validate_migration_target(url)
                self.assertNotIn("secret", str(caught.exception))
                self.assertNotIn(url, str(caught.exception))

    def test_initial_migration_is_forward_only_and_idempotent(self) -> None:
        engine = _RecordingEngine()
        url = "mysql+pymysql://user:secret@localhost/zhihui_crawler_test"

        first = run_migrations(engine, url)
        statement_count = len(engine.connection.driver_sql)
        second = run_migrations(engine, url)

        expected_versions = (
            INITIAL_MIGRATION_VERSION,
            "0002_static_fetch",
            "0003_analysis_risk_assets",
            "0004_review_publish",
            "0005_review_integrity",
            "0006_analysis_traceability",
        )
        self.assertEqual(first.applied_versions, expected_versions)
        self.assertEqual(first.skipped_versions, ())
        self.assertEqual(second.applied_versions, ())
        self.assertEqual(second.skipped_versions, expected_versions)
        self.assertGreater(statement_count, 5)
        self.assertEqual(len(engine.connection.driver_sql), statement_count + 1)

    def test_migration_refuses_engine_and_configured_url_mismatch(self) -> None:
        engine = _RecordingEngine(
            "mysql+pymysql://user:engine-secret@localhost/nav_site"
        )

        with self.assertRaises(MigrationSafetyError) as caught:
            run_migrations(
                engine,
                "mysql+pymysql://user:configured-secret@localhost/"
                "zhihui_crawler_test",
            )

        self.assertEqual(engine.connection.driver_sql, [])
        self.assertNotIn("engine-secret", str(caught.exception))
        self.assertNotIn("configured-secret", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
