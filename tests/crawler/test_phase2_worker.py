from __future__ import annotations

from datetime import timedelta
import threading
import unittest

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.crawler.config import CrawlerSettings
from backend.crawler.db import CrawlTask, DiscoveredLink, FetchResult
from backend.crawler.errors import CrawlerError
from backend.crawler.fetch.http import HttpFetchResult
from backend.crawler.fetch.robots import RobotsDecision
from backend.crawler.queue.states import CANCELLED, COMPLETED, DEAD, FAILED, LEASED
from backend.crawler.queue.tasks import enqueue_task, lease_tasks, renew_task_lease
from backend.crawler.workers.static import StaticCrawlerWorker, StaticTaskHandler
from tests.crawler.support import NOW, make_sqlite_engine


class FakeFetcher:
    def fetch(self, url, *, cancel_event=None):
        body = b"""<html lang='zh'><title>Seed</title><body>
        <a href='/next'>next</a><a href='https://outside.example/x'>outside</a>
        <link rel='alternate' type='application/rss+xml' href='/feed.xml'>
        </body></html>"""
        return HttpFetchResult(
            requested_url=url,
            normalized_url=url,
            final_url=url,
            status_code=200,
            content_type="text/html",
            charset="utf-8",
            body=body,
            bytes_read=len(body),
            redirect_chain=(),
            elapsed_ms=2,
            etag=None,
            last_modified=None,
            robots=RobotsDecision(True, 200, None, ("https://example.com/sitemap.xml",), NOW, NOW),
        )


def settings():
    return CrawlerSettings.from_env({"CRAWLER_DOMAIN_DELAY_SECONDS": "0.001"})


class StaticHandlerTests(unittest.TestCase):
    def test_html_result_links_and_same_origin_tasks_are_persisted(self) -> None:
        engine = make_sqlite_engine()
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        try:
            with factory.begin() as session:
                task = enqueue_task(
                    session,
                    task_type="static_fetch",
                    target="https://example.com/",
                    payload={
                        "target_url": "https://example.com/",
                        "normalized_url": "https://example.com/",
                        "depth": 0,
                        "parent_url": None,
                        "run_uid": "unit-run",
                        "max_depth": 2,
                        "max_pages": 20,
                        "discovery_policy": "same_origin",
                    },
                    available_at=NOW,
                ).task
                leased = lease_tasks(
                    session,
                    worker_id="worker-a",
                    task_types=["static_fetch"],
                    limit=1,
                    lease_seconds=60,
                    now=NOW,
                )[0]

            handler = StaticTaskHandler(fetcher=FakeFetcher(), settings=settings())
            prepared = handler.prepare(leased, threading.Event())
            with factory.begin() as session:
                current = session.scalar(select(CrawlTask).where(CrawlTask.id == task.id))
                persisted = handler.persist(session, current, prepared, now=NOW)

            with factory() as session:
                result = session.scalar(select(FetchResult))
                links = list(session.scalars(select(DiscoveredLink)).all())
                tasks = list(session.scalars(select(CrawlTask)).all())
            self.assertEqual(persisted.result_uid, result.result_uid)
            self.assertEqual(result.title, "Seed")
            self.assertEqual(len(links), 4)
            queued_targets = {item.target for item in tasks if item.id != task.id}
            self.assertEqual(
                queued_targets,
                {
                    "https://example.com/next",
                    "https://example.com/feed.xml",
                    "https://example.com/sitemap.xml",
                },
            )
            self.assertNotIn("https://outside.example/x", queued_targets)
        finally:
            engine.dispose()


class LeaseRenewalTests(unittest.TestCase):
    def test_owner_can_renew_but_other_worker_cannot(self) -> None:
        engine = make_sqlite_engine()
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        try:
            with factory.begin() as session:
                enqueue_task(session, task_type="static_fetch", target="https://example.com/", available_at=NOW)
                task = lease_tasks(
                    session,
                    worker_id="owner",
                    task_types=["static_fetch"],
                    limit=1,
                    lease_seconds=5,
                    now=NOW,
                )[0]
                renewed = renew_task_lease(
                    session,
                    task_uid=task.task_uid,
                    worker_id="owner",
                    lease_seconds=20,
                    now=NOW + timedelta(seconds=1),
                )
                self.assertEqual(renewed.leased_until, NOW + timedelta(seconds=21))
                with self.assertRaises(ValueError):
                    renew_task_lease(
                        session,
                        task_uid=task.task_uid,
                        worker_id="other",
                        lease_seconds=20,
                        now=NOW,
                    )
        finally:
            engine.dispose()


class FakeWorkerHandler:
    def __init__(self, error=None):
        self.error = error
        self.processed = []
        self.lock = threading.Lock()

    def prepare(self, task, cancel_event):
        if cancel_event.is_set():
            from backend.crawler.errors import Cancelled
            raise Cancelled()
        if self.error is not None:
            raise self.error
        return task.task_uid

    def persist(self, session, task, prepared, *, now):
        with self.lock:
            self.processed.append(prepared)
        return None


class WorkerRuntimeTests(unittest.TestCase):
    def _factory_with_task(self):
        engine = make_sqlite_engine()
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        with factory.begin() as session:
            task = enqueue_task(
                session,
                task_type="static_fetch",
                target="https://example.com/",
                payload={"target_url": "https://example.com/", "normalized_url": "https://example.com/", "depth": 0},
                available_at=NOW,
            ).task
        return engine, factory, task.task_uid

    def test_success_permanent_transient_and_cancel_are_distinct(self) -> None:
        cases = (
            (None, COMPLETED, "completed"),
            (CrawlerError("unsupported_content_type", "binary"), DEAD, "dead"),
            (CrawlerError("read_timeout", "timeout", retryable=True), FAILED, "retry_wait"),
        )
        for error, expected_status, expected_state in cases:
            with self.subTest(expected=expected_status):
                engine, factory, task_uid = self._factory_with_task()
                try:
                    worker = StaticCrawlerWorker(
                        session_factory=factory,
                        handler=FakeWorkerHandler(error),
                        settings=settings(),
                        worker_id="worker-one",
                        clock=lambda: NOW,
                    )
                    outcome = worker.process_one()
                    with factory() as session:
                        task = session.scalar(select(CrawlTask).where(CrawlTask.task_uid == task_uid))
                    self.assertEqual(outcome.state, expected_state)
                    self.assertEqual(task.status, expected_status)
                finally:
                    engine.dispose()

        engine, factory, task_uid = self._factory_with_task()
        try:
            event = threading.Event()
            event.set()
            outcome = StaticCrawlerWorker(
                session_factory=factory,
                handler=FakeWorkerHandler(),
                settings=settings(),
                worker_id="worker-cancel",
                clock=lambda: NOW,
            ).process_one(cancel_event=event)
            with factory() as session:
                task = session.scalar(select(CrawlTask).where(CrawlTask.task_uid == task_uid))
            self.assertEqual(outcome.state, "cancelled")
            self.assertEqual(task.status, CANCELLED)
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
