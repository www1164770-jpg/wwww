from __future__ import annotations

from datetime import timedelta
import unittest

from backend.crawler.queue.states import CANCELLED, COMPLETED, DEAD, FAILED, PENDING
from backend.crawler.queue.tasks import (
    TaskLeaseOwnershipError,
    cancel_task,
    complete_task,
    enqueue_task,
    fail_task,
    lease_tasks,
    retry_delay_seconds,
    retry_due_failed_tasks,
)
from backend.crawler.scheduler.runs import create_run, request_run_stop
from tests.crawler.support import NOW, sqlite_session


def lease_one(session, *, run_id=None, max_attempts=3):
    task = enqueue_task(
        session,
        task_type="fetch_url",
        target=f"https://task-{max_attempts}-{run_id}.example/",
        run_id=run_id,
        available_at=NOW,
    ).task
    task.max_attempts = max_attempts
    session.flush()
    return lease_tasks(
        session,
        worker_id="worker-a",
        task_types=["fetch_url"],
        limit=1,
        lease_seconds=60,
        now=NOW,
    )[0]


class TaskCompletionTests(unittest.TestCase):
    def test_owning_worker_completes_task_and_updates_run_counter(self) -> None:
        with sqlite_session() as session:
            run = create_run(
                session,
                run_uid="completion-run",
                scheduled_for=NOW,
                target_count=1,
                now=NOW,
            ).run
            task = lease_one(session, run_id=run.id)
            request_run_stop(session, run_uid=run.run_uid, now=NOW)

            completed = complete_task(
                session,
                task_uid=task.task_uid,
                worker_id="worker-a",
                now=NOW + timedelta(seconds=5),
            )

            self.assertEqual(completed.status, COMPLETED)
            self.assertEqual(completed.completed_at, NOW + timedelta(seconds=5))
            self.assertIsNone(completed.active_dedupe_key)
            self.assertIsNone(completed.leased_at)
            self.assertIsNone(completed.leased_until)
            self.assertEqual(run.completed_count, 1)
            self.assertEqual(
                lease_tasks(
                    session,
                    worker_id="worker-b",
                    task_types=["fetch_url"],
                    limit=1,
                    lease_seconds=60,
                    now=NOW + timedelta(seconds=6),
                ),
                [],
            )

    def test_non_owning_worker_cannot_complete_or_fail_task(self) -> None:
        with sqlite_session() as session:
            task = lease_one(session)

            with self.assertRaises(TaskLeaseOwnershipError):
                complete_task(
                    session,
                    task_uid=task.task_uid,
                    worker_id="worker-b",
                    now=NOW,
                )
            with self.assertRaises(TaskLeaseOwnershipError):
                fail_task(
                    session,
                    task_uid=task.task_uid,
                    worker_id="worker-b",
                    error_code="network",
                    error_message="timeout",
                    now=NOW,
                    random_value=0.5,
                )


class TaskFailureTests(unittest.TestCase):
    def test_retry_delay_is_exponential_capped_and_jittered(self) -> None:
        self.assertEqual(retry_delay_seconds(1, random_value=0.5), 30.0)
        self.assertEqual(retry_delay_seconds(2, random_value=0.5), 60.0)
        self.assertEqual(retry_delay_seconds(20, random_value=0.5), 3600.0)
        self.assertEqual(retry_delay_seconds(1, random_value=0.0), 27.0)
        self.assertEqual(retry_delay_seconds(1, random_value=1.0), 33.0)

    def test_retryable_failure_increments_attempt_and_sanitizes_error(self) -> None:
        with sqlite_session() as session:
            task = lease_one(session)
            unsafe_message = (
                "Authorization: Bearer private-token; "
                "Cookie=session=private-cookie; password=hunter2\n"
                "<html>complete response body</html>"
            )

            failed = fail_task(
                session,
                task_uid=task.task_uid,
                worker_id="worker-a",
                error_code="password=private-error-code",
                error_message=unsafe_message,
                now=NOW + timedelta(seconds=5),
                random_value=0.5,
            )

            self.assertEqual(failed.status, FAILED)
            self.assertEqual(failed.attempt_count, 1)
            self.assertEqual(
                failed.available_at,
                NOW + timedelta(seconds=35),
            )
            self.assertEqual(failed.last_error_code, "invalid_error_code")
            self.assertNotIn("private-error-code", failed.last_error_code)
            self.assertLessEqual(len(failed.last_error_message), 1000)
            self.assertNotIn("private-token", failed.last_error_message)
            self.assertNotIn("private-cookie", failed.last_error_message)
            self.assertNotIn("hunter2", failed.last_error_message)
            self.assertNotIn("complete response body", failed.last_error_message)
            self.assertIsNone(failed.worker_id)
            self.assertIsNone(failed.leased_at)
            self.assertIsNone(failed.leased_until)

    def test_due_failed_task_returns_to_pending_once(self) -> None:
        with sqlite_session() as session:
            task = lease_one(session)
            failed = fail_task(
                session,
                task_uid=task.task_uid,
                worker_id="worker-a",
                error_code="timeout",
                error_message="timed out",
                now=NOW,
                random_value=0.5,
            )

            self.assertEqual(retry_due_failed_tasks(session, now=NOW), 0)
            self.assertEqual(
                retry_due_failed_tasks(
                    session,
                    now=failed.available_at,
                ),
                1,
            )
            self.assertEqual(failed.status, PENDING)
            self.assertEqual(
                retry_due_failed_tasks(
                    session,
                    now=failed.available_at,
                ),
                0,
            )

    def test_reaching_max_attempts_moves_task_to_dead(self) -> None:
        with sqlite_session() as session:
            run = create_run(
                session,
                run_uid="dead-run",
                scheduled_for=NOW,
                target_count=1,
                now=NOW,
            ).run
            task = lease_one(session, run_id=run.id, max_attempts=1)

            dead = fail_task(
                session,
                task_uid=task.task_uid,
                worker_id="worker-a",
                error_code="permanent",
                error_message="failed",
                now=NOW,
                random_value=0.5,
            )

            self.assertEqual(dead.status, DEAD)
            self.assertEqual(dead.attempt_count, 1)
            self.assertIsNone(dead.active_dedupe_key)
            self.assertEqual(run.failed_count, 1)

    def test_only_pending_or_failed_tasks_can_be_cancelled(self) -> None:
        with sqlite_session() as session:
            pending = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://pending-cancel.example/",
                available_at=NOW,
            ).task
            cancelled = cancel_task(
                session,
                task_uid=pending.task_uid,
                now=NOW,
            )
            self.assertEqual(cancelled.status, CANCELLED)
            self.assertIsNone(cancelled.active_dedupe_key)

            leased = lease_one(session)
            failed = fail_task(
                session,
                task_uid=leased.task_uid,
                worker_id="worker-a",
                error_code="timeout",
                error_message="timeout",
                now=NOW,
                random_value=0.5,
            )
            self.assertEqual(
                cancel_task(session, task_uid=failed.task_uid, now=NOW).status,
                CANCELLED,
            )

            with self.assertRaises(ValueError):
                cancel_task(
                    session,
                    task_uid=cancelled.task_uid,
                    now=NOW,
                )


if __name__ == "__main__":
    unittest.main()
