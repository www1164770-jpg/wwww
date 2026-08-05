from __future__ import annotations

import argparse
from contextlib import contextmanager
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

import backend.crawler.cli as cli
from backend.crawler.db import CrawlerBase, CrawlTask, WorkerHeartbeat
from backend.crawler.errors import CrawlerError


EXPECTED_COMMANDS = {
    "db-check",
    "migrate",
    "enqueue-smoke-task",
    "lease-smoke-task",
    "recover-expired",
    "worker-status",
    "run-create",
    "run-stop",
    "status",
    "enqueue-url",
    "fetch-once",
    "worker-once",
    "worker-run",
    "task-show",
    "result-show",
    "analysis-once",
    "analysis-run",
    "icon-once",
    "icon-run",
    "review-create",
    "review-list",
    "review-show",
    "review-assign",
    "review-approve",
    "review-reject",
    "publish-preview",
    "publish-enqueue",
    "publish-status",
    "publish-retry",
    "integration-readiness",
}


def parse_single_json(stream: io.StringIO) -> dict:
    lines = stream.getvalue().splitlines()
    if len(lines) != 1:
        raise AssertionError(f"expected one JSON line, got {lines!r}")
    return json.loads(lines[0])


@contextmanager
def sqlite_cli_environment():
    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        database_path = root / "crawler-test.sqlite3"
        database_url = f"sqlite:///{database_path.as_posix()}"
        engine = create_engine(database_url)
        CrawlerBase.metadata.create_all(engine)
        environment = {
            "CRAWLER_DATABASE_URL": database_url,
            "CRAWLER_LOG_ROOT": str(root / "logs"),
            "CRAWLER_ICON_ROOT": str(root / "icons"),
            "CRAWLER_WORKER_ID": "cli-worker",
        }
        try:
            with patch.object(cli, "create_crawler_engine", return_value=engine):
                yield engine, environment
        finally:
            engine.dispose()


def run_json(arguments, environment):
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = cli.main(
        [*arguments, "--json"],
        environ=environment,
        stdout=stdout,
        stderr=stderr,
    )
    stream = stdout if exit_code == 0 else stderr
    return exit_code, parse_single_json(stream), stdout, stderr


class CrawlerCliTests(unittest.TestCase):
    def test_parser_preserves_phase_one_and_adds_phase_two_and_three_commands(self) -> None:
        parser = cli.build_parser()
        subparsers = next(
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        )

        self.assertEqual(set(subparsers.choices), EXPECTED_COMMANDS)

    def test_missing_database_configuration_is_clear_safe_and_nonzero(self) -> None:
        exit_code, payload, stdout, stderr = run_json(["status"], {})

        self.assertNotEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "configuration_error")
        self.assertIn("CRAWLER_DATABASE_URL", payload["error"]["message"])
        self.assertNotIn("mysql://", stderr.getvalue())

    def test_database_error_is_not_reported_as_an_empty_queue(self) -> None:
        environment = {
            "CRAWLER_DATABASE_URL": (
                "mysql+pymysql://crawler:private-password@localhost/"
                "zhihui_crawler"
            ),
            "CRAWLER_LOG_ROOT": str(Path(tempfile.gettempdir()) / "crawler-cli-test"),
        }
        database_error = OperationalError(
            "SELECT 1",
            {},
            RuntimeError(
                "mysql+pymysql://crawler:private-password@localhost/"
                "zhihui_crawler"
            ),
        )
        with patch.object(
            cli,
            "create_crawler_engine",
            side_effect=database_error,
        ):
            exit_code, payload, stdout, stderr = run_json(
                ["lease-smoke-task"],
                environment,
            )

        self.assertNotEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "database_unavailable")
        self.assertNotIn("task", payload.get("data", {}))
        self.assertNotIn("private-password", stderr.getvalue())
        self.assertNotIn("mysql+pymysql://", stderr.getvalue())

    def test_empty_lease_is_a_successful_empty_result(self) -> None:
        with sqlite_cli_environment() as (_engine, environment):
            exit_code, payload, _stdout, _stderr = run_json(
                ["lease-smoke-task"],
                environment,
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["state"], "empty")
        self.assertIsNone(payload["data"]["task"])

    def test_status_json_is_valid_and_does_not_register_worker(self) -> None:
        with sqlite_cli_environment() as (engine, environment):
            exit_code, payload, _stdout, _stderr = run_json(
                ["status"],
                environment,
            )
            with Session(engine) as session:
                worker_count = session.scalar(
                    select(func.count()).select_from(WorkerHeartbeat)
                )

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["command"], "status")
        self.assertEqual(payload["data"]["tasks"], {})
        self.assertEqual(payload["data"]["outbox"], {})
        self.assertIsNone(payload["data"]["active_run"])
        self.assertEqual(worker_count, 0)

    def test_run_enqueue_lease_stop_and_worker_status_commands_share_contract(
        self,
    ) -> None:
        with sqlite_cli_environment() as (_engine, environment):
            create_code, created, _stdout, _stderr = run_json(
                ["run-create"],
                environment,
            )
            enqueue_code, enqueued, _stdout, _stderr = run_json(
                ["enqueue-smoke-task"],
                environment,
            )
            lease_code, leased, _stdout, _stderr = run_json(
                ["lease-smoke-task"],
                environment,
            )
            worker_code, workers, _stdout, _stderr = run_json(
                ["worker-status"],
                environment,
            )
            stop_code, stopped, _stdout, _stderr = run_json(
                ["run-stop"],
                environment,
            )

        self.assertEqual(
            (create_code, enqueue_code, lease_code, worker_code, stop_code),
            (0, 0, 0, 0, 0),
        )
        self.assertTrue(created["data"]["created"])
        self.assertTrue(enqueued["data"]["created"])
        self.assertEqual(leased["data"]["state"], "leased")
        self.assertEqual(
            leased["data"]["task"]["task_uid"],
            enqueued["data"]["task_uid"],
        )
        self.assertEqual(workers["data"]["workers"][0]["worker_id"], "cli-worker")
        self.assertTrue(stopped["data"]["stop_requested"])
        self.assertEqual(
            stopped["data"]["run_uid"],
            created["data"]["run_uid"],
        )

    def test_db_check_and_recovery_commands_return_machine_readable_counts(
        self,
    ) -> None:
        with sqlite_cli_environment() as (_engine, environment):
            db_code, checked, _stdout, _stderr = run_json(
                ["db-check"],
                environment,
            )
            recovery_code, recovered, _stdout, _stderr = run_json(
                ["recover-expired"],
                environment,
            )

        self.assertEqual((db_code, recovery_code), (0, 0))
        self.assertEqual(checked["data"]["database"], "ok")
        self.assertEqual(recovered["data"]["recovered_count"], 0)
        self.assertEqual(recovered["data"]["dead_count"], 0)

    def test_enqueue_smoke_task_uses_configured_max_attempts(self) -> None:
        with sqlite_cli_environment() as (engine, environment):
            environment["CRAWLER_MAX_ATTEMPTS"] = "7"
            exit_code, payload, _stdout, _stderr = run_json(
                ["enqueue-smoke-task"],
                environment,
            )
            with Session(engine) as session:
                task = session.scalar(
                    select(CrawlTask).where(
                        CrawlTask.task_uid == payload["data"]["task_uid"]
                    )
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(task.max_attempts, 7)

    def test_enqueue_url_is_idempotent_and_redacts_query_in_cli_output(self) -> None:
        with sqlite_cli_environment() as (_engine, environment):
            first_code, first, _stdout, _stderr = run_json(
                ["enqueue-url", "HTTPS://Example.com:443/path?token=secret&utm_source=x#part"],
                environment,
            )
            second_code, second, _stdout, _stderr = run_json(
                ["enqueue-url", "https://example.com/path?token=secret"],
                environment,
            )
            show_code, shown, _stdout, _stderr = run_json(
                ["task-show", first["data"]["task_uid"]],
                environment,
            )

        self.assertEqual((first_code, second_code, show_code), (0, 0, 0))
        self.assertTrue(first["data"]["created"])
        self.assertFalse(second["data"]["created"])
        self.assertEqual(first["data"]["task_uid"], second["data"]["task_uid"])
        self.assertEqual(first["data"]["normalized_url"], "https://example.com/path?[REDACTED]")
        self.assertNotIn("secret", json.dumps(shown))

    def test_worker_once_empty_has_stable_json_shape(self) -> None:
        with sqlite_cli_environment() as (_engine, environment):
            code, payload, _stdout, _stderr = run_json(["worker-once"], environment)

        self.assertEqual(code, 0)
        self.assertEqual(payload["data"]["processed_count"], 0)
        self.assertEqual(payload["data"]["outcomes"][0]["state"], "empty")

    def test_phase_three_worker_commands_are_bounded_and_empty_is_success(self) -> None:
        with sqlite_cli_environment() as (_engine, environment):
            results = {
                command: run_json([command], environment)[:2]
                for command in ("analysis-once", "icon-once")
            }
            status_code, status, _stdout, _stderr = run_json(["status"], environment)

        for command, (code, payload) in results.items():
            with self.subTest(command=command):
                self.assertEqual(code, 0)
                self.assertEqual(payload["data"]["processed_count"], 0)
                self.assertEqual(payload["data"]["outcomes"][0]["state"], "empty")
        self.assertEqual(status_code, 0)
        self.assertEqual(status["data"]["analysis_results"], 0)
        self.assertEqual(status["data"]["risk_decisions"], 0)
        self.assertEqual(status["data"]["icon_assets"], 0)

    def test_fetch_once_uses_real_queue_worker_lifecycle_and_fetch_exit_code(self) -> None:
        class CompletingHandler:
            def prepare(self, task, cancel_event):
                return task.task_uid

            def persist(self, session, task, prepared, *, now):
                return SimpleNamespace(result_uid="result-from-handler")

        with sqlite_cli_environment() as (engine, environment):
            with patch.object(cli, "build_static_handler", return_value=CompletingHandler()):
                code, payload, _stdout, _stderr = run_json(
                    ["fetch-once", "https://example.com/page"],
                    environment,
                )
            with Session(engine) as session:
                task = session.scalar(
                    select(CrawlTask).where(CrawlTask.task_uid == payload["data"]["task_uid"])
                )

        self.assertEqual(code, 0)
        self.assertEqual(payload["data"]["state"], "completed")
        self.assertEqual(payload["data"]["result_uid"], "result-from-handler")
        self.assertEqual(task.status, "completed")

        class FailingHandler:
            def prepare(self, task, cancel_event):
                raise CrawlerError("unsupported_content_type", "binary")

        with sqlite_cli_environment() as (_engine, environment):
            with patch.object(cli, "build_static_handler", return_value=FailingHandler()):
                failure_code, failed, stdout, stderr = run_json(
                    ["fetch-once", "https://example.com/binary"],
                    environment,
                )
        self.assertEqual(failure_code, 5)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(failed["error"]["code"], "fetch_error")
        self.assertNotIn("binary", stderr.getvalue())

    def test_invalid_url_uses_input_exit_code(self) -> None:
        with sqlite_cli_environment() as (_engine, environment):
            code, payload, _stdout, _stderr = run_json(
                ["enqueue-url", "file:///private"],
                environment,
            )
        self.assertEqual(code, 4)
        self.assertEqual(payload["error"]["code"], "command_rejected")

    def test_migrate_refuses_formal_project_database_without_leaking_url(
        self,
    ) -> None:
        environment = {
            "CRAWLER_DATABASE_URL": (
                "mysql+pymysql://formal-user:private-password@localhost/nav_site"
            ),
            "CRAWLER_LOG_ROOT": str(Path(tempfile.gettempdir()) / "crawler-cli-test"),
        }
        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = cli.main(
            ["migrate", "--json"],
            environ=environment,
            stdout=stdout,
            stderr=stderr,
        )
        payload = parse_single_json(stderr)

        self.assertNotEqual(exit_code, 0)
        self.assertEqual(payload["error"]["code"], "migration_refused")
        self.assertNotIn("private-password", stderr.getvalue())
        self.assertNotIn("formal-user", stderr.getvalue())
        self.assertNotIn("nav_site", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
