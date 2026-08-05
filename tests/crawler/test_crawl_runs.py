from __future__ import annotations

from datetime import timedelta
import unittest

from backend.crawler.scheduler.runs import (
    COMPLETED,
    FAILED,
    RUNNING,
    STOP_REQUESTED,
    RunStateError,
    create_run,
    finish_run,
    get_active_run,
    request_run_stop,
)
from tests.crawler.support import NOW, sqlite_session


class CrawlRunTests(unittest.TestCase):
    def test_create_run_is_idempotent_by_run_uid(self) -> None:
        with sqlite_session() as session:
            first = create_run(
                session,
                run_uid="night-20260730",
                scheduled_for=NOW,
                target_count=3000,
                now=NOW,
            )
            duplicate = create_run(
                session,
                run_uid="night-20260730",
                scheduled_for=NOW + timedelta(days=1),
                target_count=99,
                now=NOW + timedelta(hours=1),
            )

            self.assertTrue(first.created)
            self.assertFalse(duplicate.created)
            self.assertEqual(first.run.id, duplicate.run.id)
            self.assertEqual(duplicate.run.target_count, 3000)
            self.assertEqual(duplicate.run.status, RUNNING)
            self.assertEqual(duplicate.run.started_at, NOW)

    def test_stop_request_is_idempotent_and_active_until_finished(self) -> None:
        with sqlite_session() as session:
            created = create_run(
                session,
                run_uid="night-stop",
                scheduled_for=NOW,
                target_count=10,
                now=NOW,
            ).run

            stopped = request_run_stop(
                session,
                run_uid=created.run_uid,
                now=NOW + timedelta(hours=4),
            )
            repeated = request_run_stop(
                session,
                run_uid=created.run_uid,
                now=NOW + timedelta(hours=5),
            )

            self.assertEqual(stopped.status, STOP_REQUESTED)
            self.assertEqual(stopped.stop_requested_at, NOW + timedelta(hours=4))
            self.assertEqual(repeated.stop_requested_at, NOW + timedelta(hours=4))
            self.assertEqual(get_active_run(session).run_uid, created.run_uid)

            finished = finish_run(
                session,
                run_uid=created.run_uid,
                status=COMPLETED,
                now=NOW + timedelta(hours=6),
            )
            self.assertEqual(finished.status, COMPLETED)
            self.assertEqual(finished.finished_at, NOW + timedelta(hours=6))
            self.assertIsNone(get_active_run(session))

    def test_finish_accepts_only_terminal_statuses(self) -> None:
        with sqlite_session() as session:
            created = create_run(
                session,
                run_uid="night-finish",
                scheduled_for=NOW,
                target_count=1,
                now=NOW,
            ).run

            with self.assertRaises(RunStateError):
                finish_run(
                    session,
                    run_uid=created.run_uid,
                    status=RUNNING,
                    now=NOW,
                )
            failed = finish_run(
                session,
                run_uid=created.run_uid,
                status=FAILED,
                now=NOW,
            )
            self.assertEqual(failed.status, FAILED)

    def test_terminal_run_cannot_be_stopped_or_finished_again(self) -> None:
        with sqlite_session() as session:
            created = create_run(
                session,
                run_uid="night-terminal",
                scheduled_for=NOW,
                target_count=1,
                now=NOW,
            ).run
            finish_run(
                session,
                run_uid=created.run_uid,
                status=COMPLETED,
                now=NOW,
            )

            with self.assertRaises(RunStateError):
                request_run_stop(
                    session,
                    run_uid=created.run_uid,
                    now=NOW,
                )
            with self.assertRaises(RunStateError):
                finish_run(
                    session,
                    run_uid=created.run_uid,
                    status=FAILED,
                    now=NOW,
                )


if __name__ == "__main__":
    unittest.main()
