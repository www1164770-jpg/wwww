from __future__ import annotations

from datetime import timedelta
import unittest

from sqlalchemy import func, select

from backend.crawler.db import WorkerHeartbeat
from backend.crawler.workers.heartbeats import (
    ONLINE,
    STALE,
    STOPPED,
    WorkerNotFound,
    heartbeat_worker,
    mark_worker_stopped,
    register_worker,
    worker_effective_status,
)
from tests.crawler.support import NOW, sqlite_session


class WorkerHeartbeatTests(unittest.TestCase):
    def test_registration_is_unique_and_reregistration_refreshes_process(self) -> None:
        with sqlite_session() as session:
            first = register_worker(
                session,
                worker_id="worker-a",
                worker_type="fetch",
                process_id=100,
                hostname="host-a",
                now=NOW,
            )
            repeated = register_worker(
                session,
                worker_id="worker-a",
                worker_type="analysis",
                process_id=200,
                hostname="host-b",
                now=NOW + timedelta(minutes=1),
            )

            self.assertEqual(first.id, repeated.id)
            self.assertEqual(
                session.scalar(select(func.count()).select_from(WorkerHeartbeat)),
                1,
            )
            self.assertEqual(repeated.worker_type, "analysis")
            self.assertEqual(repeated.process_id, 200)
            self.assertEqual(repeated.hostname, "host-b")
            self.assertEqual(repeated.status, ONLINE)
            self.assertEqual(repeated.started_at, NOW + timedelta(minutes=1))
            self.assertEqual(repeated.last_seen_at, NOW + timedelta(minutes=1))

    def test_heartbeat_updates_last_seen_and_current_task(self) -> None:
        with sqlite_session() as session:
            worker = register_worker(
                session,
                worker_id="worker-a",
                worker_type="fetch",
                process_id=100,
                hostname="host-a",
                now=NOW,
            )

            updated = heartbeat_worker(
                session,
                worker_id=worker.worker_id,
                now=NOW + timedelta(seconds=30),
                current_task_uid="task-123",
            )

            self.assertEqual(updated.last_seen_at, NOW + timedelta(seconds=30))
            self.assertEqual(updated.current_task_uid, "task-123")
            self.assertEqual(updated.status, ONLINE)

    def test_effective_status_distinguishes_online_stale_and_stopped(self) -> None:
        with sqlite_session() as session:
            worker = register_worker(
                session,
                worker_id="worker-a",
                worker_type="fetch",
                process_id=100,
                hostname="host-a",
                now=NOW,
            )

            self.assertEqual(
                worker_effective_status(
                    worker,
                    now=NOW + timedelta(seconds=59),
                    stale_after_seconds=60,
                ),
                ONLINE,
            )
            self.assertEqual(
                worker_effective_status(
                    worker,
                    now=NOW + timedelta(seconds=61),
                    stale_after_seconds=60,
                ),
                STALE,
            )

            stopped = mark_worker_stopped(
                session,
                worker_id=worker.worker_id,
                now=NOW + timedelta(seconds=70),
            )
            self.assertEqual(stopped.status, STOPPED)
            self.assertIsNone(stopped.current_task_uid)
            self.assertEqual(
                worker_effective_status(
                    stopped,
                    now=NOW + timedelta(days=1),
                    stale_after_seconds=60,
                ),
                STOPPED,
            )

    def test_heartbeat_does_not_implicitly_restart_stopped_worker(self) -> None:
        with sqlite_session() as session:
            worker = register_worker(
                session,
                worker_id="worker-a",
                worker_type="fetch",
                process_id=100,
                hostname="host-a",
                now=NOW,
            )
            mark_worker_stopped(
                session,
                worker_id=worker.worker_id,
                now=NOW + timedelta(seconds=1),
            )

            heartbeat = heartbeat_worker(
                session,
                worker_id=worker.worker_id,
                now=NOW + timedelta(seconds=2),
                current_task_uid="ignored-while-stopped",
            )

            self.assertEqual(heartbeat.status, STOPPED)
            self.assertIsNone(heartbeat.current_task_uid)

    def test_metadata_is_recursively_redacted_before_persistence(self) -> None:
        metadata = {
            "runtime": "python",
            "Password": "private-password",
            "nested": {
                "Authorization": "Bearer private-token",
                "safe": "visible",
            },
            "cookies": [{"Cookie": "private-cookie"}],
        }
        with sqlite_session() as session:
            worker = register_worker(
                session,
                worker_id="worker-a",
                worker_type="fetch",
                process_id=100,
                hostname="host-a",
                now=NOW,
                metadata=metadata,
            )

            stored = str(worker.metadata_json)
            self.assertIn("visible", stored)
            self.assertNotIn("private-password", stored)
            self.assertNotIn("private-token", stored)
            self.assertNotIn("private-cookie", stored)
            self.assertGreaterEqual(stored.count("[REDACTED]"), 3)

    def test_unknown_worker_heartbeat_and_stop_are_rejected(self) -> None:
        with sqlite_session() as session:
            with self.assertRaises(WorkerNotFound):
                heartbeat_worker(
                    session,
                    worker_id="missing",
                    now=NOW,
                )
            with self.assertRaises(WorkerNotFound):
                mark_worker_stopped(
                    session,
                    worker_id="missing",
                    now=NOW,
                )


if __name__ == "__main__":
    unittest.main()
