from __future__ import annotations

from datetime import timedelta
import unittest

from backend.crawler.queue.states import DEAD, LEASED, PENDING
from backend.crawler.queue.tasks import (
    enqueue_task,
    lease_tasks,
    recover_expired_leases,
)
from tests.crawler.support import NOW, sqlite_session


class ExpiredLeaseRecoveryTests(unittest.TestCase):
    def test_expired_lease_returns_to_pending_and_clears_lease_fields(self) -> None:
        with sqlite_session() as session:
            task = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://recover.example/",
                available_at=NOW,
            ).task
            lease_tasks(
                session,
                worker_id="worker-a",
                task_types=["fetch_url"],
                limit=1,
                lease_seconds=10,
                now=NOW,
            )

            result = recover_expired_leases(
                session,
                now=NOW + timedelta(seconds=11),
                random_value=0.5,
            )

            self.assertEqual(result.recovered_count, 1)
            self.assertEqual(result.dead_count, 0)
            self.assertEqual(task.status, PENDING)
            self.assertEqual(task.attempt_count, 1)
            self.assertEqual(
                task.available_at,
                NOW + timedelta(seconds=41),
            )
            self.assertIsNone(task.worker_id)
            self.assertIsNone(task.leased_at)
            self.assertIsNone(task.leased_until)

    def test_recovery_is_strictly_expired_and_idempotent(self) -> None:
        with sqlite_session() as session:
            task = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://boundary.example/",
                available_at=NOW,
            ).task
            lease_tasks(
                session,
                worker_id="worker-a",
                task_types=["fetch_url"],
                limit=1,
                lease_seconds=10,
                now=NOW,
            )

            at_boundary = recover_expired_leases(
                session,
                now=NOW + timedelta(seconds=10),
                random_value=0.5,
            )
            after_boundary = recover_expired_leases(
                session,
                now=NOW + timedelta(seconds=11),
                random_value=0.5,
            )
            repeated = recover_expired_leases(
                session,
                now=NOW + timedelta(seconds=12),
                random_value=0.5,
            )

            self.assertEqual(at_boundary.recovered_count, 0)
            self.assertEqual(after_boundary.recovered_count, 1)
            self.assertEqual(repeated.recovered_count, 0)
            self.assertEqual(task.attempt_count, 1)

    def test_expired_lease_at_max_attempts_becomes_dead(self) -> None:
        with sqlite_session() as session:
            task = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://dead-recovery.example/",
                available_at=NOW,
            ).task
            task.max_attempts = 1
            session.flush()
            lease_tasks(
                session,
                worker_id="worker-a",
                task_types=["fetch_url"],
                limit=1,
                lease_seconds=10,
                now=NOW,
            )

            result = recover_expired_leases(
                session,
                now=NOW + timedelta(seconds=11),
                random_value=0.5,
            )

            self.assertEqual(result.recovered_count, 0)
            self.assertEqual(result.dead_count, 1)
            self.assertEqual(task.status, DEAD)
            self.assertEqual(task.attempt_count, 1)
            self.assertIsNone(task.active_dedupe_key)

    def test_non_expired_leased_task_is_unchanged(self) -> None:
        with sqlite_session() as session:
            task = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://active-lease.example/",
                available_at=NOW,
            ).task
            lease_tasks(
                session,
                worker_id="worker-a",
                task_types=["fetch_url"],
                limit=1,
                lease_seconds=60,
                now=NOW,
            )

            result = recover_expired_leases(
                session,
                now=NOW + timedelta(seconds=1),
                random_value=0.5,
            )

            self.assertEqual(result.recovered_count, 0)
            self.assertEqual(result.dead_count, 0)
            self.assertEqual(task.status, LEASED)
            self.assertEqual(task.attempt_count, 0)


if __name__ == "__main__":
    unittest.main()
