from __future__ import annotations

from datetime import timedelta
import unittest

from backend.crawler.outbox.service import (
    DEAD,
    LEASED,
    PENDING,
    PROCESSED,
    OutboxLeaseOwnershipError,
    enqueue_outbox_event,
    fail_outbox_event,
    lease_outbox_events,
    mark_outbox_processed,
)
from tests.crawler.support import NOW, sqlite_session


class OutboxTests(unittest.TestCase):
    def test_event_uid_is_idempotent_and_payload_is_copied(self) -> None:
        payload = {"site_uid": "site-1", "nested": {"approved": True}}
        with sqlite_session() as session:
            first = enqueue_outbox_event(
                session,
                event_uid="event-1",
                aggregate_type="candidate_site",
                aggregate_uid="site-1",
                event_type="site_approved",
                payload=payload,
                available_at=NOW,
            )
            payload["nested"]["approved"] = False
            duplicate = enqueue_outbox_event(
                session,
                event_uid="event-1",
                aggregate_type="candidate_site",
                aggregate_uid="site-other",
                event_type="different",
                payload={"replacement": True},
                available_at=NOW,
            )

            self.assertTrue(first.created)
            self.assertFalse(duplicate.created)
            self.assertEqual(first.event.id, duplicate.event.id)
            self.assertEqual(
                duplicate.event.payload_json,
                {"site_uid": "site-1", "nested": {"approved": True}},
            )

    def test_only_due_pending_events_are_leased_in_stable_order(self) -> None:
        with sqlite_session() as session:
            later_created = enqueue_outbox_event(
                session,
                event_uid="event-later-created",
                aggregate_type="site",
                aggregate_uid="site-1",
                event_type="approved",
                payload={},
                available_at=NOW - timedelta(seconds=10),
            ).event
            earlier_created = enqueue_outbox_event(
                session,
                event_uid="event-earlier-created",
                aggregate_type="site",
                aggregate_uid="site-2",
                event_type="approved",
                payload={},
                available_at=NOW - timedelta(seconds=10),
            ).event
            later_created.created_at = NOW - timedelta(seconds=5)
            earlier_created.created_at = NOW - timedelta(seconds=20)
            future = enqueue_outbox_event(
                session,
                event_uid="event-future",
                aggregate_type="site",
                aggregate_uid="site-3",
                event_type="approved",
                payload={},
                available_at=NOW + timedelta(seconds=1),
            ).event
            session.flush()

            leased = lease_outbox_events(
                session,
                worker_id="outbox-a",
                limit=10,
                lease_seconds=60,
                now=NOW,
            )

            self.assertEqual(
                [event.event_uid for event in leased],
                ["event-earlier-created", "event-later-created"],
            )
            self.assertTrue(all(event.status == LEASED for event in leased))
            self.assertTrue(all(event.worker_id == "outbox-a" for event in leased))
            self.assertTrue(all(event.leased_at == NOW for event in leased))
            self.assertTrue(
                all(
                    event.leased_until == NOW + timedelta(seconds=60)
                    for event in leased
                )
            )
            self.assertEqual(future.status, PENDING)

    def test_processed_event_is_never_leased_again(self) -> None:
        with sqlite_session() as session:
            event = enqueue_outbox_event(
                session,
                event_uid="event-processed",
                aggregate_type="site",
                aggregate_uid="site-1",
                event_type="approved",
                payload={},
                available_at=NOW,
            ).event
            lease_outbox_events(
                session,
                worker_id="outbox-a",
                limit=1,
                lease_seconds=60,
                now=NOW,
            )

            processed = mark_outbox_processed(
                session,
                event_uid=event.event_uid,
                worker_id="outbox-a",
                now=NOW + timedelta(seconds=1),
            )

            self.assertEqual(processed.status, PROCESSED)
            self.assertEqual(processed.processed_at, NOW + timedelta(seconds=1))
            self.assertEqual(
                lease_outbox_events(
                    session,
                    worker_id="outbox-b",
                    limit=1,
                    lease_seconds=60,
                    now=NOW + timedelta(seconds=2),
                ),
                [],
            )

    def test_wrong_worker_cannot_process_or_fail_event(self) -> None:
        with sqlite_session() as session:
            event = enqueue_outbox_event(
                session,
                event_uid="event-owner",
                aggregate_type="site",
                aggregate_uid="site-1",
                event_type="approved",
                payload={},
                available_at=NOW,
            ).event
            lease_outbox_events(
                session,
                worker_id="outbox-a",
                limit=1,
                lease_seconds=60,
                now=NOW,
            )

            with self.assertRaises(OutboxLeaseOwnershipError):
                mark_outbox_processed(
                    session,
                    event_uid=event.event_uid,
                    worker_id="outbox-b",
                    now=NOW,
                )
            with self.assertRaises(OutboxLeaseOwnershipError):
                fail_outbox_event(
                    session,
                    event_uid=event.event_uid,
                    worker_id="outbox-b",
                    error_message="failed",
                    now=NOW,
                    random_value=0.5,
                )

    def test_failure_retries_then_reaching_max_attempts_becomes_dead(self) -> None:
        with sqlite_session() as session:
            event = enqueue_outbox_event(
                session,
                event_uid="event-retry",
                aggregate_type="site",
                aggregate_uid="site-1",
                event_type="approved",
                payload={"body": "must never be copied to error"},
                available_at=NOW,
            ).event
            event.max_attempts = 2
            session.flush()
            lease_outbox_events(
                session,
                worker_id="outbox-a",
                limit=1,
                lease_seconds=60,
                now=NOW,
            )

            retried = fail_outbox_event(
                session,
                event_uid=event.event_uid,
                worker_id="outbox-a",
                error_message="password=private-value\nfull response body",
                now=NOW,
                random_value=0.5,
            )

            self.assertEqual(retried.status, PENDING)
            self.assertEqual(retried.attempt_count, 1)
            self.assertEqual(retried.available_at, NOW + timedelta(seconds=30))
            self.assertNotIn("private-value", retried.last_error)
            self.assertNotIn("full response body", retried.last_error)
            self.assertNotIn("must never", retried.last_error)

            lease_outbox_events(
                session,
                worker_id="outbox-b",
                limit=1,
                lease_seconds=60,
                now=retried.available_at,
            )
            dead = fail_outbox_event(
                session,
                event_uid=event.event_uid,
                worker_id="outbox-b",
                error_message="permanent",
                now=retried.available_at,
                random_value=0.5,
            )
            self.assertEqual(dead.status, DEAD)
            self.assertEqual(dead.attempt_count, 2)

    def test_lease_batch_and_duration_are_bounded(self) -> None:
        with sqlite_session() as session:
            for limit, duration in ((0, 60), (101, 60), (1, 0)):
                with self.subTest(limit=limit, duration=duration):
                    with self.assertRaises(ValueError):
                        lease_outbox_events(
                            session,
                            worker_id="worker",
                            limit=limit,
                            lease_seconds=duration,
                            now=NOW,
                        )


if __name__ == "__main__":
    unittest.main()
