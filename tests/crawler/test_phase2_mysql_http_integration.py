from __future__ import annotations

import os
import threading
import unittest
from uuid import uuid4

from sqlalchemy import delete, func, select, text
from sqlalchemy.engine import make_url

from backend.crawler.config import CrawlerSettings
from backend.crawler.db import (
    CrawlRun,
    CrawlTask,
    DiscoveredLink,
    FetchResult,
    WorkerHeartbeat,
    utc_now,
)
from backend.crawler.db.migration import run_migrations
from backend.crawler.db.session import create_crawler_engine, create_session_factory
from backend.crawler.discovery.enqueue import enqueue_discovered_task
from backend.crawler.net.url import normalize_http_url
from backend.crawler.queue.states import CANCELLED, COMPLETED, DEAD
from backend.crawler.errors import Cancelled
from backend.crawler.queue.tasks import recover_expired_leases
from backend.crawler.scheduler.runs import (
    CANCELLED as RUN_CANCELLED,
    COMPLETED as RUN_COMPLETED,
    create_run,
    finish_run,
    request_run_stop,
)
from backend.crawler.workers.factory import build_static_handler
from backend.crawler.workers.static import StaticCrawlerWorker
from tests.crawler.phase2_http_server import LocalOnlyTransport, PhaseTwoHttpServer


MYSQL_TEST_URL = os.environ.get("CRAWLER_TEST_DATABASE_URL", "").strip()


@unittest.skipUnless(
    MYSQL_TEST_URL,
    "CRAWLER_TEST_DATABASE_URL is not configured; Phase 2 MySQL integration skipped",
)
class PhaseTwoMySQLHttpIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if make_url(MYSQL_TEST_URL).database != "zhihui_crawler_test":
            raise AssertionError("Phase 2 integration requires exactly zhihui_crawler_test")
        environment = dict(os.environ)
        environment["CRAWLER_DATABASE_URL"] = MYSQL_TEST_URL
        environment.update(
            {
                "CRAWLER_DOMAIN_DELAY_SECONDS": "0.001",
                "CRAWLER_CONNECT_TIMEOUT_SECONDS": "2",
                "CRAWLER_READ_TIMEOUT_SECONDS": "2",
                "CRAWLER_MAX_RESPONSE_BYTES": "1048576",
                "CRAWLER_MAX_RETRIES": "2",
                "CRAWLER_MAX_DEPTH": "2",
                "CRAWLER_MAX_PAGES_PER_ORIGIN": "20",
                "CRAWLER_MAX_URLS_PER_RUN": "100",
            }
        )
        cls.settings = CrawlerSettings.from_env(environment, require_database=True)
        cls.engine = create_crawler_engine(cls.settings)
        with cls.engine.connect() as connection:
            if connection.execute(text("SELECT DATABASE()")).scalar_one() != "zhihui_crawler_test":
                raise AssertionError("actual MySQL database is not zhihui_crawler_test")
        run_migrations(cls.engine, MYSQL_TEST_URL)
        cls.factory = create_session_factory(cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        self.prefix = "p2-" + uuid4().hex[:16]
        self.run_uids: list[str] = []
        self.worker_ids: list[str] = []

    def tearDown(self) -> None:
        with self.factory.begin() as session:
            run_ids = list(
                session.scalars(
                    select(CrawlRun.id).where(CrawlRun.run_uid.in_(self.run_uids))
                ).all()
            )
            task_ids = list(
                session.scalars(select(CrawlTask.id).where(CrawlTask.run_id.in_(run_ids))).all()
            ) if run_ids else []
            result_ids = list(
                session.scalars(select(FetchResult.id).where(FetchResult.task_id.in_(task_ids))).all()
            ) if task_ids else []
            if result_ids:
                session.execute(delete(DiscoveredLink).where(DiscoveredLink.source_result_id.in_(result_ids)))
                session.execute(delete(FetchResult).where(FetchResult.id.in_(result_ids)))
            if task_ids:
                session.execute(delete(CrawlTask).where(CrawlTask.id.in_(task_ids)))
            if run_ids:
                session.execute(delete(CrawlRun).where(CrawlRun.id.in_(run_ids)))
            if self.worker_ids:
                session.execute(delete(WorkerHeartbeat).where(WorkerHeartbeat.worker_id.in_(self.worker_ids)))

    def _crawl(self, server: PhaseTwoHttpServer, handler, suffix: str):
        run_uid = f"{self.prefix}-{suffix}"
        self.run_uids.append(run_uid)
        root = server.origin + "/"
        with self.factory.begin() as session:
            run = create_run(
                session,
                run_uid=run_uid,
                scheduled_for=utc_now(),
                target_count=100,
                now=utc_now(),
            ).run
            normalized = normalize_http_url(root)
            seed = enqueue_discovered_task(
                session,
                task_type="static_fetch",
                target=normalized.url,
                payload={
                    "target_url": normalized.url,
                    "normalized_url": normalized.url,
                    "depth": 0,
                    "parent_url": None,
                    "run_uid": run_uid,
                    "max_depth": 2,
                    "max_pages": 20,
                    "discovery_policy": "same_origin",
                },
                run_id=run.id,
            )
            run_id = run.id

        worker_ids = [f"{self.prefix}-{suffix}-a", f"{self.prefix}-{suffix}-b"]
        self.worker_ids.extend(worker_ids)
        outcomes: list = []
        failures: list[BaseException] = []
        barrier = threading.Barrier(2)

        def run_worker(worker_id: str) -> None:
            try:
                barrier.wait()
                worker = StaticCrawlerWorker(
                    session_factory=self.factory,
                    handler=handler,
                    settings=self.settings,
                    worker_id=worker_id,
                )
                outcomes.extend(worker.run(max_jobs=50))
            except BaseException as error:
                failures.append(error)

        threads = [threading.Thread(target=run_worker, args=(worker_id,)) for worker_id in worker_ids]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(failures, [])

        with self.factory.begin() as session:
            tasks = list(session.scalars(select(CrawlTask).where(CrawlTask.run_id == run_id)).all())
            repeated = enqueue_discovered_task(
                session,
                task_type="static_fetch",
                target=normalize_http_url(root).url,
                payload=seed.task.payload_json,
                run_id=run_id,
            )
            finish_run(session, run_uid=run_uid, status=RUN_COMPLETED, now=utc_now())

        self.assertFalse(repeated.created)
        self.assertTrue(tasks)
        self.assertTrue(all(task.status in {COMPLETED, DEAD, CANCELLED} for task in tasks))
        self.assertFalse(any(task.status in {"pending", "leased", "running", "failed"} for task in tasks))
        identities = [(task.task_type, task.target_hash) for task in tasks]
        self.assertEqual(len(identities), len(set(identities)))
        processed_ids = [outcome.task_uid for outcome in outcomes if outcome.task_uid]
        self.assertEqual(len(processed_ids), len(set(processed_ids)))
        return run_id, tasks, outcomes

    def test_two_workers_complete_bounded_static_crawl_and_content_deduplication(self) -> None:
        with PhaseTwoHttpServer() as server:
            handler = build_static_handler(
                self.settings,
                resolver=lambda _host, _port: ["93.184.216.34"],
                transport=LocalOnlyTransport(server.server.server_port),
            )
            try:
                first_run, first_tasks, first_outcomes = self._crawl(server, handler, "one")
                self.assertEqual(server.site.counts.get("/blocked", 0), 0)
                self.assertGreaterEqual(len(first_outcomes), 8)

                root = normalize_http_url(server.origin + "/")
                with self.factory() as session:
                    first_root_results = list(
                        session.scalars(
                            select(FetchResult).where(
                                FetchResult.normalized_final_fingerprint == root.fingerprint,
                                FetchResult.status == "success",
                            )
                        ).all()
                    )
                    external = list(
                        session.scalars(
                            select(DiscoveredLink).where(DiscoveredLink.is_same_origin.is_(False))
                        ).all()
                    )
                    external_tasks = list(
                        session.scalars(
                            select(CrawlTask).where(
                                CrawlTask.run_id == first_run,
                                CrawlTask.target.like("%external.example%"),
                            )
                        ).all()
                    )
                    document_types = {
                        (item.document_metadata_json or {}).get("document_type")
                        for item in session.scalars(select(FetchResult).where(FetchResult.status == "success")).all()
                    }
                self.assertEqual(len(first_root_results), 1)
                first_hash = first_root_results[0].content_hash
                self.assertTrue(external)
                self.assertEqual(external_tasks, [])
                self.assertIn("feed", document_types)
                self.assertTrue({"urlset", "index"} & document_types)

                self._crawl(server, handler, "two")
                with self.factory() as session:
                    unchanged_count = session.scalar(
                        select(func.count()).select_from(FetchResult).where(
                            FetchResult.normalized_final_fingerprint == root.fingerprint,
                            FetchResult.status == "success",
                        )
                    )
                self.assertEqual(unchanged_count, 1)

                server.site.version = 2
                self._crawl(server, handler, "three")
                with self.factory() as session:
                    changed = list(
                        session.scalars(
                            select(FetchResult).where(
                                FetchResult.normalized_final_fingerprint == root.fingerprint,
                                FetchResult.status == "success",
                            )
                        ).all()
                    )
                self.assertEqual(len(changed), 2)
                self.assertEqual(len({item.content_hash for item in changed}), 2)
                self.assertIn(first_hash, {item.content_hash for item in changed})
            finally:
                handler.fetcher.close()

    def _short_lease_settings(self) -> CrawlerSettings:
        environment = dict(os.environ)
        environment["CRAWLER_DATABASE_URL"] = MYSQL_TEST_URL
        environment["CRAWLER_LEASE_SECONDS"] = "1"
        environment["CRAWLER_DOMAIN_DELAY_SECONDS"] = "0.001"
        return CrawlerSettings.from_env(environment, require_database=True)

    def _one_worker_task(self, suffix: str):
        run_uid = f"{self.prefix}-{suffix}"
        self.run_uids.append(run_uid)
        with self.factory.begin() as session:
            run = create_run(
                session,
                run_uid=run_uid,
                scheduled_for=utc_now(),
                target_count=1,
                now=utc_now(),
            ).run
            task = enqueue_discovered_task(
                session,
                task_type="static_fetch",
                target="https://example.com/long",
                payload={
                    "target_url": "https://example.com/long",
                    "normalized_url": "https://example.com/long",
                    "depth": 0,
                    "run_uid": run_uid,
                },
                run_id=run.id,
            ).task
        return run_uid, task.task_uid

    def test_long_task_renews_lease_and_stop_requested_cancels_handler(self) -> None:
        class WaitingHandler:
            def __init__(self, *, stop_on_cancel: bool):
                self.started = threading.Event()
                self.stop_on_cancel = stop_on_cancel

            def prepare(self, task, cancel_event):
                self.started.set()
                if self.stop_on_cancel:
                    if cancel_event.wait(5):
                        raise Cancelled()
                    raise AssertionError("stop_requested did not cancel handler")
                if cancel_event.wait(1.6):
                    raise Cancelled()
                return task.task_uid

            def persist(self, session, task, prepared, *, now):
                return None

        short = self._short_lease_settings()
        run_uid, task_uid = self._one_worker_task("renew")
        renew_handler = WaitingHandler(stop_on_cancel=False)
        renew_worker_id = f"{self.prefix}-renew-worker"
        self.worker_ids.append(renew_worker_id)
        renew_worker = StaticCrawlerWorker(
            session_factory=self.factory,
            handler=renew_handler,
            settings=short,
            worker_id=renew_worker_id,
        )
        renew_outcome: list = []
        thread = threading.Thread(target=lambda: renew_outcome.append(renew_worker.process_one()))
        thread.start()
        self.assertTrue(renew_handler.started.wait(3))
        threading.Event().wait(1.1)
        with self.factory.begin() as session:
            task = session.scalar(select(CrawlTask).where(CrawlTask.task_uid == task_uid))
            self.assertGreater(task.leased_until, utc_now())
            recovered = recover_expired_leases(session, now=utc_now())
            self.assertEqual((recovered.recovered_count, recovered.dead_count), (0, 0))
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(renew_outcome[0].state, "completed")
        with self.factory.begin() as session:
            finish_run(session, run_uid=run_uid, status=RUN_COMPLETED, now=utc_now())

        stop_run_uid, stop_task_uid = self._one_worker_task("stop")
        stop_handler = WaitingHandler(stop_on_cancel=True)
        stop_worker_id = f"{self.prefix}-stop-worker"
        self.worker_ids.append(stop_worker_id)
        stop_worker = StaticCrawlerWorker(
            session_factory=self.factory,
            handler=stop_handler,
            settings=short,
            worker_id=stop_worker_id,
        )
        stop_outcome: list = []
        thread = threading.Thread(target=lambda: stop_outcome.append(stop_worker.process_one()))
        thread.start()
        self.assertTrue(stop_handler.started.wait(3))
        with self.factory.begin() as session:
            request_run_stop(session, run_uid=stop_run_uid, now=utc_now())
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(stop_outcome[0].state, "cancelled")
        with self.factory.begin() as session:
            task = session.scalar(select(CrawlTask).where(CrawlTask.task_uid == stop_task_uid))
            self.assertEqual(task.status, CANCELLED)
            finish_run(session, run_uid=stop_run_uid, status=RUN_CANCELLED, now=utc_now())


if __name__ == "__main__":
    unittest.main()
