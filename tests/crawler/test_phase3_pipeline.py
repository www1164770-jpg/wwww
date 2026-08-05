from __future__ import annotations

import threading
import unittest

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.crawler.analysis.worker import AnalysisCrawlerWorker
from backend.crawler.config import CrawlerSettings
from backend.crawler.db import AnalysisResult, CrawlTask, RiskDecision
from backend.crawler.fetch.http import HttpFetchResult
from backend.crawler.fetch.robots import RobotsDecision
from backend.crawler.queue.states import COMPLETED, PENDING
from backend.crawler.queue.tasks import enqueue_task
from backend.crawler.workers.static import StaticCrawlerWorker, StaticTaskHandler
from tests.crawler.support import NOW, make_sqlite_engine


class RichEducationFetcher:
    def fetch(self, url, *, cancel_event=None):
        body = """<html lang='zh-CN'><title>开放课程与学习资源</title>
        <meta name='description' content='提供大学课程、学习资料和教师工具。'>
        <h1>免费教育资源</h1><p>汇集课程、学习资料、教师工具和大学公开课，内容详细可靠。</p>
        <link rel='icon' href='/favicon.png'></html>""".encode()
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
            robots=RobotsDecision(True, 200, None, (), NOW, NOW),
        )


def settings(*, icon_fetch_enabled: bool = False):
    return CrawlerSettings.from_env(
        {
            "CRAWLER_DOMAIN_DELAY_SECONDS": "0.001",
            "CRAWLER_ANALYSIS_ENABLED": "true",
            "CRAWLER_ICON_FETCH_ENABLED": "true" if icon_fetch_enabled else "false",
        }
    )


class PhaseThreePipelineTests(unittest.TestCase):
    def test_static_completion_enqueues_and_analysis_worker_persists_decision(self) -> None:
        engine = make_sqlite_engine()
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        try:
            with factory.begin() as session:
                static = enqueue_task(
                    session,
                    task_type="static_fetch",
                    target="https://example.com/",
                    payload={
                        "target_url": "https://example.com/",
                        "normalized_url": "https://example.com/",
                        "depth": 0,
                        "run_uid": "phase3-unit",
                    },
                    available_at=NOW,
                ).task
            static_outcome = StaticCrawlerWorker(
                session_factory=factory,
                handler=StaticTaskHandler(fetcher=RichEducationFetcher(), settings=settings()),
                settings=settings(),
                worker_id="static-phase3",
                clock=lambda: NOW,
            ).process_one(cancel_event=threading.Event())
            self.assertEqual(static_outcome.state, "completed")

            with factory() as session:
                analysis_task = session.scalar(
                    select(CrawlTask).where(CrawlTask.task_type == "analysis")
                )
                self.assertIsNotNone(analysis_task)
                self.assertEqual(analysis_task.status, PENDING)
                self.assertEqual(analysis_task.payload_json["schema_version"], "phase3-analysis-task-v2")
                self.assertEqual(analysis_task.payload_json["task_contract"], "content_analysis")
                self.assertNotIn("text_excerpt", analysis_task.payload_json)

            analysis_outcome = AnalysisCrawlerWorker(
                session_factory=factory,
                settings=settings(),
                worker_id="analysis-phase3",
                clock=lambda: NOW,
            ).process_one()
            self.assertEqual(analysis_outcome.state, "completed")

            with factory() as session:
                stored_task = session.scalar(
                    select(CrawlTask).where(CrawlTask.task_type == "analysis")
                )
                analysis = session.scalar(select(AnalysisResult))
                decision = session.scalar(select(RiskDecision))
                self.assertEqual(stored_task.status, COMPLETED)
                self.assertEqual(analysis.category, "education")
                self.assertEqual(analysis.model_status, "not_needed")
                self.assertEqual(decision.status, "approved")
                self.assertFalse(decision.hard_reject)
        finally:
            engine.dispose()

    def test_same_analysis_version_is_not_requeued_after_completion(self) -> None:
        engine = make_sqlite_engine()
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        try:
            with factory.begin() as session:
                enqueue_task(
                    session,
                    task_type="static_fetch",
                    target="https://example.com/",
                    payload={"target_url": "https://example.com/", "depth": 0, "run_uid": "same"},
                    available_at=NOW,
                )
            static_worker = StaticCrawlerWorker(
                session_factory=factory,
                handler=StaticTaskHandler(fetcher=RichEducationFetcher(), settings=settings()),
                settings=settings(),
                worker_id="static-same",
                clock=lambda: NOW,
            )
            self.assertEqual(static_worker.process_one().state, "completed")
            analysis_worker = AnalysisCrawlerWorker(
                session_factory=factory,
                settings=settings(),
                worker_id="analysis-same",
                clock=lambda: NOW,
            )
            self.assertEqual(analysis_worker.process_one().state, "completed")

            with factory.begin() as session:
                from backend.crawler.analysis.persistence import enqueue_analysis_task
                from backend.crawler.db import FetchResult

                fetch = session.scalar(select(FetchResult))
                result = enqueue_analysis_task(session, fetch_result=fetch, run_id=None)
                self.assertIsNone(result)
        finally:
            engine.dispose()

    def test_icon_task_is_enqueued_only_when_risk_is_not_rejected(self) -> None:
        class RiskFetcher(RichEducationFetcher):
            def fetch(self, url, *, cancel_event=None):
                fetched = super().fetch(url, cancel_event=cancel_event)
                body = b"""<html lang='en'><title>Online casino gambling</title>
                <meta name='description' content='Online casino gambling and betting portal'>
                <p>Online casino gambling and betting.</p>
                <link rel='icon' href='/favicon.png'></html>"""
                return HttpFetchResult(
                    requested_url=fetched.requested_url,
                    normalized_url=fetched.normalized_url,
                    final_url=fetched.final_url,
                    status_code=200,
                    content_type="text/html",
                    charset="utf-8",
                    body=body,
                    bytes_read=len(body),
                    redirect_chain=(),
                    elapsed_ms=2,
                    etag=None,
                    last_modified=None,
                    robots=fetched.robots,
                )

        for fetcher, expected_icons, expected_decision in (
            (RichEducationFetcher(), 1, "approved"),
            (RiskFetcher(), 0, "rejected"),
        ):
            with self.subTest(expected_decision=expected_decision):
                engine = make_sqlite_engine()
                factory = sessionmaker(bind=engine, expire_on_commit=False)
                try:
                    with factory.begin() as session:
                        enqueue_task(
                            session,
                            task_type="static_fetch",
                            target="https://example.com/",
                            payload={
                                "target_url": "https://example.com/",
                                "depth": 0,
                                "run_uid": expected_decision,
                            },
                            available_at=NOW,
                        )
                    configured = settings(icon_fetch_enabled=True)
                    self.assertEqual(
                        StaticCrawlerWorker(
                            session_factory=factory,
                            handler=StaticTaskHandler(fetcher=fetcher, settings=configured),
                            settings=configured,
                            worker_id=f"static-{expected_decision}",
                            clock=lambda: NOW,
                        ).process_one().state,
                        "completed",
                    )
                    self.assertEqual(
                        AnalysisCrawlerWorker(
                            session_factory=factory,
                            settings=configured,
                            worker_id=f"analysis-{expected_decision}",
                            clock=lambda: NOW,
                        ).process_one().state,
                        "completed",
                    )
                    with factory() as session:
                        decision = session.scalar(select(RiskDecision))
                        icons = list(
                            session.scalars(
                                select(CrawlTask).where(CrawlTask.task_type == "icon_fetch")
                            ).all()
                        )
                    self.assertEqual(decision.status, expected_decision)
                    self.assertEqual(len(icons), expected_icons)
                finally:
                    engine.dispose()


if __name__ == "__main__":
    unittest.main()
