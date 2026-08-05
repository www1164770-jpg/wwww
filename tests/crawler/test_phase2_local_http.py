from __future__ import annotations

import threading
import unittest

from backend.crawler.config import CrawlerSettings
from backend.crawler.errors import CrawlerError
from backend.crawler.workers.factory import build_static_handler
from tests.crawler.phase2_http_server import LocalOnlyTransport, PhaseTwoHttpServer


class LocalHttpIntegrationTests(unittest.TestCase):
    def test_real_http_server_obeys_production_policy_via_test_transport(self) -> None:
        with PhaseTwoHttpServer() as server:
            settings = CrawlerSettings.from_env(
                {
                    "CRAWLER_DOMAIN_DELAY_SECONDS": "0.001",
                    "CRAWLER_MAX_RESPONSE_BYTES": "2048",
                    "CRAWLER_MAX_RETRIES": "2",
                }
            )
            handler = build_static_handler(
                settings,
                resolver=lambda _host, _port: ["93.184.216.34"],
                transport=LocalOnlyTransport(server.server.server_port),
            )
            fetcher = handler.fetcher
            try:
                root = fetcher.fetch(server.origin + "/")
                redirected = fetcher.fetch(server.origin + "/redirect")
                compressed = fetcher.fetch(server.origin + "/gzip")
                retried = fetcher.fetch(server.origin + "/retry-after")
                recovered = fetcher.fetch(server.origin + "/flaky")
                self.assertIn(b"Seed", root.body)
                self.assertTrue(redirected.final_url.endswith("/page-2"))
                self.assertEqual(compressed.body, b"<title>gzip</title>")
                self.assertIn(b"retry ok", retried.body)
                self.assertIn(b"flaky ok", recovered.body)

                for path, code in (
                    ("/blocked", "robots_denied"),
                    ("/binary", "unsupported_content_type"),
                    ("/large", "response_too_large"),
                    ("/redirect-loop", "redirect_loop"),
                ):
                    with self.subTest(path=path):
                        with self.assertRaises(CrawlerError) as caught:
                            fetcher.fetch(server.origin + path, cancel_event=threading.Event())
                        self.assertEqual(caught.exception.code, code)
                self.assertEqual(server.site.counts.get("/blocked", 0), 0)
            finally:
                fetcher.close()


if __name__ == "__main__":
    unittest.main()
