from __future__ import annotations

import unittest

from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from backend.crawler.db import CrawlTask, DiscoveredLink, FetchResult
from backend.crawler.fetch.persistence import persist_discovered_links, persist_fetch_result
from backend.crawler.discovery.html import parse_html
from backend.crawler.discovery.links import DiscoveryPolicy, select_discovered_links
from backend.crawler.fetch.http import HttpFetchResult
from backend.crawler.fetch.robots import RobotsDecision
from backend.crawler.queue.tasks import enqueue_task
from tests.crawler.support import NOW, make_sqlite_engine, sqlite_session


def fetched(body="<title>中文 🚀</title>".encode(), final="https://example.com/"):
    return HttpFetchResult(
        requested_url="https://example.com/",
        normalized_url="https://example.com/",
        final_url=final,
        status_code=200,
        content_type="text/html",
        charset="utf-8",
        body=body,
        bytes_read=len(body),
        redirect_chain=(final,) if final != "https://example.com/" else (),
        elapsed_ms=5,
        etag='"abc"',
        last_modified="Fri, 01 Aug 2026 00:00:00 GMT",
        robots=RobotsDecision(True, 200, 1.0, (), NOW, NOW),
    )


class PhaseTwoSchemaTests(unittest.TestCase):
    def test_models_have_foreign_keys_unique_constraints_json_and_bigint(self) -> None:
        engine = make_sqlite_engine()
        try:
            inspector = inspect(engine)
            self.assertIn("fetch_results", inspector.get_table_names())
            self.assertIn("discovered_links", inspector.get_table_names())
            fetch_unique = {
                tuple(item["column_names"])
                for item in inspector.get_unique_constraints("fetch_results")
            }
            links_unique = {
                tuple(item["column_names"])
                for item in inspector.get_unique_constraints("discovered_links")
            }
            self.assertIn(("task_id",), fetch_unique)
            self.assertIn(("normalized_final_fingerprint", "content_hash"), fetch_unique)
            self.assertIn(("source_result_id", "normalized_fingerprint"), links_unique)
            self.assertTrue(inspector.get_foreign_keys("fetch_results"))
            self.assertTrue(inspector.get_foreign_keys("discovered_links"))
        finally:
            engine.dispose()

    def test_retry_and_unchanged_content_do_not_duplicate_results_or_links(self) -> None:
        with sqlite_session() as session:
            first_task = enqueue_task(session, task_type="static_fetch", target="https://example.com/").task
            document = parse_html(
                "<title>中文 🚀</title><a href='/next'>次へ</a>",
                final_url="https://example.com/",
            )
            first = persist_fetch_result(session, task=first_task, fetch=fetched(), document=document, fetched_at=NOW)
            retry = persist_fetch_result(session, task=first_task, fetch=fetched(), document=document, fetched_at=NOW)
            candidates = select_discovered_links(
                document.links,
                source_url="https://example.com/",
                depth=0,
                policy=DiscoveryPolicy(),
            )
            created_one = persist_discovered_links(session, result=first.result, links=candidates, discovered_at=NOW)
            created_two = persist_discovered_links(session, result=first.result, links=candidates, discovered_at=NOW)

            first_task.active_dedupe_key = None
            first_task.status = "completed"
            second_task = enqueue_task(session, task_type="static_fetch", target="https://example.com/").task
            unchanged = persist_fetch_result(session, task=second_task, fetch=fetched(), document=document, fetched_at=NOW)

            self.assertTrue(first.created)
            self.assertFalse(retry.created)
            self.assertFalse(retry.updated)
            self.assertEqual((created_one, created_two), (1, 0))
            self.assertFalse(unchanged.created)
            self.assertEqual(unchanged.result.id, first.result.id)
            self.assertEqual(len(session.scalars(select(FetchResult)).all()), 1)
            self.assertEqual(len(session.scalars(select(DiscoveredLink)).all()), 1)
            stored = session.scalar(select(FetchResult))
            self.assertEqual(stored.title, "中文 🚀")
            self.assertIsInstance(stored.redirect_chain, list)

    def test_database_constraints_reject_duplicate_source_link(self) -> None:
        with sqlite_session() as session:
            task = enqueue_task(session, task_type="static_fetch", target="https://example.com/").task
            document = parse_html("<title>x</title>", final_url="https://example.com/")
            result = persist_fetch_result(session, task=task, fetch=fetched(), document=document, fetched_at=NOW).result
            common = dict(
                source_result_id=result.id,
                source_url="https://example.com/",
                discovered_url="https://example.com/x",
                normalized_url="https://example.com/x",
                normalized_fingerprint="a" * 64,
                relation_type="anchor",
                discovery_type="html_anchor",
                depth=1,
                is_safe=True,
                is_same_origin=True,
                enqueue_status="recorded",
                metadata_json={},
                discovered_at=NOW,
            )
            session.add(DiscoveredLink(link_uid="one", **common))
            session.flush()
            with session.begin_nested():
                session.add(DiscoveredLink(link_uid="two", **common))
                with self.assertRaises(IntegrityError):
                    session.flush()


if __name__ == "__main__":
    unittest.main()
