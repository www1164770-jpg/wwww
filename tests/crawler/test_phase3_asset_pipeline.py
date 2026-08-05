from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import struct
import tempfile
import unittest

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.crawler.assets import store_icon
from backend.crawler.assets.persistence import enqueue_icon_task
from backend.crawler.assets.worker import IconCrawlerWorker
from backend.crawler.config import CrawlerSettings
from backend.crawler.db import CrawlTask, FetchResult, IconAsset
from backend.crawler.discovery.html import parse_html
from backend.crawler.fetch.http import HttpFetchResult
from backend.crawler.fetch.persistence import persist_fetch_result
from backend.crawler.fetch.robots import RobotsDecision
from backend.crawler.queue.states import COMPLETED
from backend.crawler.queue.tasks import enqueue_task
from tests.crawler.support import NOW, make_sqlite_engine


def png() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
        + struct.pack(">II", 16, 16) + b"\x08\x06\x00\x00\x00"
        + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def add_fetch(session) -> FetchResult:
    task = enqueue_task(
        session,
        task_type="static_fetch",
        target="https://example.com/",
        available_at=NOW,
    ).task
    body = b"<title>Example</title><link rel='icon' href='/favicon.png'>"
    fetch = HttpFetchResult(
        requested_url="https://example.com/",
        normalized_url="https://example.com/",
        final_url="https://example.com/",
        status_code=200,
        content_type="text/html",
        charset="utf-8",
        body=body,
        bytes_read=len(body),
        redirect_chain=(),
        elapsed_ms=1,
        etag=None,
        last_modified=None,
        robots=RobotsDecision(True, 200, None, (), NOW, NOW),
    )
    return persist_fetch_result(
        session,
        task=task,
        fetch=fetch,
        document=parse_html(body, final_url=fetch.final_url),
        fetched_at=NOW,
    ).result


class FakeDownloader:
    def __init__(self):
        self.calls = []

    def download(self, url, *, root):
        self.calls.append((url, root))
        return store_icon(
            png(),
            declared_mime="image/png",
            source_url=url,
            root=root,
        )


class PhaseThreeAssetPipelineTests(unittest.TestCase):
    def test_icon_worker_downloads_persists_and_completes_task(self) -> None:
        engine = make_sqlite_engine()
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            crawler_settings = replace(CrawlerSettings.from_env({}), icon_root=root)
            downloader = FakeDownloader()
            try:
                with factory.begin() as session:
                    fetch = add_fetch(session)
                    queued = enqueue_icon_task(
                        session,
                        fetch_result=fetch,
                        source_url=fetch.favicon_url,
                        run_id=None,
                        available_at=NOW,
                    )
                    self.assertTrue(queued.created)

                outcome = IconCrawlerWorker(
                    session_factory=factory,
                    settings=crawler_settings,
                    downloader=downloader,
                    worker_id="icon-unit",
                    clock=lambda: NOW,
                ).process_one()
                self.assertEqual(outcome.state, "completed")
                self.assertEqual(len(downloader.calls), 1)

                with factory.begin() as session:
                    asset = session.scalar(select(IconAsset))
                    task = session.scalar(
                        select(CrawlTask).where(CrawlTask.task_type == "icon_fetch")
                    )
                    self.assertEqual(task.status, COMPLETED)
                    self.assertTrue((root / asset.relative_path).is_file())
                    fetch = session.scalar(select(FetchResult))
                    self.assertIsNone(
                        enqueue_icon_task(
                            session,
                            fetch_result=fetch,
                            source_url=fetch.favicon_url,
                            run_id=None,
                        )
                    )
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
