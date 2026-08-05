from __future__ import annotations

from datetime import timedelta
import unittest

from sqlalchemy.exc import IntegrityError

from backend.crawler.queue.states import COMPLETED
from backend.crawler.queue.tasks import (
    enqueue_task,
    normalize_task_target,
    task_target_hash,
)
from tests.crawler.support import NOW, sqlite_session


class TaskTargetNormalizationTests(unittest.TestCase):
    def test_http_targets_have_stable_basic_normalization(self) -> None:
        cases = (
            (" HTTPS://Example.COM:443#section ", "https://example.com/"),
            (
                "http://Example.com:80/path?q=two#fragment",
                "http://example.com/path?q=two",
            ),
            ("https://Example.com:8443/a", "https://example.com:8443/a"),
            ("custom target ", "custom target"),
        )

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(normalize_task_target(value), expected)

    def test_blank_target_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            normalize_task_target("   ")

    def test_target_hash_is_sha256_of_normalized_target(self) -> None:
        self.assertEqual(
            task_target_hash("https://example.com/"),
            "0f115db062b7c0dd030b16878c99dea5c354b49dc37b38eb8846179c7783e9d7",
        )


class TaskEnqueueTests(unittest.TestCase):
    def test_duplicate_active_task_returns_existing_row(self) -> None:
        with sqlite_session() as session:
            first = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://EXAMPLE.com#first",
                payload={"source": "directory"},
                available_at=NOW,
            )
            second = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://example.com/",
                payload={"source": "other"},
                available_at=NOW + timedelta(hours=1),
            )

            self.assertTrue(first.created)
            self.assertFalse(second.created)
            self.assertEqual(second.task.id, first.task.id)
            self.assertEqual(second.task.payload_json, {"source": "directory"})
            self.assertEqual(second.task.available_at, NOW)

    def test_same_target_can_be_active_for_different_task_types(self) -> None:
        with sqlite_session() as session:
            fetch = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://example.com/",
                available_at=NOW,
            )
            analyze = enqueue_task(
                session,
                task_type="analyze_snapshot",
                target="https://example.com/",
                available_at=NOW,
            )

            self.assertTrue(fetch.created)
            self.assertTrue(analyze.created)
            self.assertNotEqual(fetch.task.id, analyze.task.id)

    def test_terminal_task_releases_active_dedupe_for_a_new_generation(self) -> None:
        with sqlite_session() as session:
            first = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://example.com/",
                available_at=NOW,
            )
            first.task.status = COMPLETED
            first.task.active_dedupe_key = None
            first.task.completed_at = NOW
            session.flush()

            refresh = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://example.com/",
                available_at=NOW + timedelta(days=1),
            )

            self.assertTrue(refresh.created)
            self.assertNotEqual(refresh.task.id, first.task.id)
            self.assertEqual(refresh.task.target_hash, first.task.target_hash)

    def test_explicit_dedupe_generation_controls_active_identity(self) -> None:
        with sqlite_session() as session:
            first = enqueue_task(
                session,
                task_type="catalog_page",
                target="page-1",
                dedupe_key="night-1",
                available_at=NOW,
            )
            second_generation = enqueue_task(
                session,
                task_type="catalog_page",
                target="page-1",
                dedupe_key="night-2",
                available_at=NOW,
            )

            self.assertTrue(first.created)
            self.assertTrue(second_generation.created)
            self.assertNotEqual(
                first.task.active_dedupe_key,
                second_generation.task.active_dedupe_key,
            )

    def test_payload_is_copied_before_it_is_stored(self) -> None:
        payload = {"source": {"name": "directory"}}
        with sqlite_session() as session:
            result = enqueue_task(
                session,
                task_type="fetch_url",
                target="https://example.com/",
                payload=payload,
                available_at=NOW,
            )
            payload["source"]["name"] = "mutated"

            self.assertEqual(
                result.task.payload_json,
                {"source": {"name": "directory"}},
            )

    def test_unrelated_database_integrity_error_is_not_reported_as_duplicate(
        self,
    ) -> None:
        with sqlite_session() as session:
            with self.assertRaises(IntegrityError):
                enqueue_task(
                    session,
                    task_type="fetch_url",
                    target="https://example.com/",
                    run_id=999999,
                    available_at=NOW,
                )

    def test_blank_task_type_is_rejected_before_inserting(self) -> None:
        with sqlite_session() as session:
            with self.assertRaises(ValueError):
                enqueue_task(
                    session,
                    task_type=" ",
                    target="https://example.com/",
                    available_at=NOW,
                )


if __name__ == "__main__":
    unittest.main()
