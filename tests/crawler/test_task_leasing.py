from __future__ import annotations

from datetime import timedelta
import unittest

from backend.crawler.queue.states import LEASED, PENDING
from backend.crawler.queue.tasks import enqueue_task, lease_tasks
from backend.crawler.scheduler.runs import create_run, request_run_stop
from tests.crawler.support import NOW, sqlite_session


class TaskLeasingTests(unittest.TestCase):
    def test_only_due_pending_tasks_are_leased_and_fields_are_set(self) -> None:
        with sqlite_session() as session:
            due = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://due.example/",
                available_at=NOW,
            ).task
            future = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://future.example/",
                available_at=NOW + timedelta(seconds=1),
            ).task

            leased = lease_tasks(
                session,
                worker_id="worker-a",
                task_types=["fetch_url"],
                limit=10,
                lease_seconds=300,
                now=NOW,
            )

            self.assertEqual([task.id for task in leased], [due.id])
            self.assertEqual(due.status, LEASED)
            self.assertEqual(due.worker_id, "worker-a")
            self.assertEqual(due.leased_at, NOW)
            self.assertEqual(due.leased_until, NOW + timedelta(seconds=300))
            self.assertEqual(future.status, PENDING)

    def test_leasing_orders_by_priority_available_created_and_id(self) -> None:
        with sqlite_session() as session:
            tasks = []
            for name, priority, available_offset, created_offset in (
                ("low-priority", 200, -10, -20),
                ("high-later-created", 10, -20, -10),
                ("high-earlier-created", 10, -20, -30),
                ("middle", 100, -30, -40),
            ):
                task = enqueue_task(
                    session,
                    task_type="fetch_url",
                    target=f"https://{name}.example/",
                    priority=priority,
                    available_at=NOW + timedelta(seconds=available_offset),
                ).task
                task.created_at = NOW + timedelta(seconds=created_offset)
                tasks.append(task)
            session.flush()

            leased = lease_tasks(
                session,
                worker_id="worker-a",
                task_types=["fetch_url"],
                limit=4,
                lease_seconds=60,
                now=NOW,
            )

            self.assertEqual(
                [task.target for task in leased],
                [
                    "https://high-earlier-created.example/",
                    "https://high-later-created.example/",
                    "https://middle.example/",
                    "https://low-priority.example/",
                ],
            )

    def test_second_worker_cannot_lease_a_task_already_leased(self) -> None:
        with sqlite_session() as session:
            enqueue_task(
                session,
                task_type="fetch_url",
                target="https://once.example/",
                available_at=NOW,
            )

            first = lease_tasks(
                session,
                worker_id="worker-a",
                task_types=["fetch_url"],
                limit=1,
                lease_seconds=60,
                now=NOW,
            )
            second = lease_tasks(
                session,
                worker_id="worker-b",
                task_types=["fetch_url"],
                limit=1,
                lease_seconds=60,
                now=NOW,
            )

            self.assertEqual(len(first), 1)
            self.assertEqual(second, [])

    def test_lease_limit_worker_types_and_duration_are_bounded(self) -> None:
        with sqlite_session() as session:
            for arguments in (
                {
                    "worker_id": "worker",
                    "task_types": ["fetch_url"],
                    "limit": 0,
                    "lease_seconds": 60,
                },
                {
                    "worker_id": "worker",
                    "task_types": ["fetch_url"],
                    "limit": 101,
                    "lease_seconds": 60,
                },
                {
                    "worker_id": " ",
                    "task_types": ["fetch_url"],
                    "limit": 1,
                    "lease_seconds": 60,
                },
                {
                    "worker_id": "worker",
                    "task_types": [],
                    "limit": 1,
                    "lease_seconds": 60,
                },
                {
                    "worker_id": "worker",
                    "task_types": ["fetch_url"],
                    "limit": 1,
                    "lease_seconds": 0,
                },
            ):
                with self.subTest(arguments=arguments):
                    with self.assertRaises(ValueError):
                        lease_tasks(session, now=NOW, **arguments)

    def test_stop_requested_run_blocks_new_leases_but_not_standalone_tasks(
        self,
    ) -> None:
        with sqlite_session() as session:
            run = create_run(
                session,
                run_uid="night-stop-leasing",
                scheduled_for=NOW,
                target_count=2,
                now=NOW,
            ).run
            run_task = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://run.example/",
                run_id=run.id,
                available_at=NOW,
            ).task
            standalone = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://standalone.example/",
                available_at=NOW,
            ).task
            request_run_stop(session, run_uid=run.run_uid, now=NOW)

            leased = lease_tasks(
                session,
                worker_id="worker-a",
                task_types=["fetch_url"],
                limit=10,
                lease_seconds=60,
                now=NOW,
            )

            self.assertEqual([task.id for task in leased], [standalone.id])
            self.assertEqual(run_task.status, PENDING)

    def test_run_leased_counter_is_updated_in_same_session(self) -> None:
        with sqlite_session() as session:
            run = create_run(
                session,
                run_uid="night-count",
                scheduled_for=NOW,
                target_count=2,
                now=NOW,
            ).run
            for suffix in ("one", "two"):
                enqueue_task(
                    session,
                    task_type="fetch_url",
                    target=f"https://{suffix}.example/",
                    run_id=run.id,
                    available_at=NOW,
                )

            leased = lease_tasks(
                session,
                worker_id="worker-a",
                task_types=["fetch_url"],
                limit=2,
                lease_seconds=60,
                now=NOW,
            )

            self.assertEqual(len(leased), 2)
            self.assertEqual(run.leased_count, 2)


if __name__ == "__main__":
    unittest.main()
