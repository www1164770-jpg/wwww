from __future__ import annotations

import unittest

from backend.crawler.config import CrawlerConfigError, CrawlerSettings


class PhaseTwoConfigTests(unittest.TestCase):
    def test_static_crawler_defaults_are_bounded(self) -> None:
        settings = CrawlerSettings.from_env({})
        self.assertEqual(settings.user_agent, "ZhiHuiNavigationBot/1.0")
        self.assertEqual(settings.global_concurrency, 5)
        self.assertEqual(settings.domain_delay_seconds, 1.0)
        self.assertEqual(settings.connect_timeout_seconds, 5.0)
        self.assertEqual(settings.read_timeout_seconds, 10.0)
        self.assertEqual(settings.max_response_bytes, 2_097_152)
        self.assertEqual(settings.max_redirects, 5)
        self.assertEqual(settings.max_depth, 2)
        self.assertEqual(settings.max_pages_per_origin, 20)
        self.assertEqual(settings.max_links_per_page, 200)
        self.assertEqual(settings.max_urls_per_run, 100)
        self.assertEqual(settings.robots_cache_seconds, 86_400)
        self.assertEqual(settings.dns_cache_seconds, 60)
        self.assertEqual(settings.max_sitemap_bytes, 5_242_880)
        self.assertEqual(settings.max_sitemap_urls, 1000)
        self.assertEqual(settings.max_sitemap_files, 20)
        self.assertEqual(settings.max_sitemap_depth, 3)
        self.assertEqual(settings.max_feed_entries, 100)
        self.assertEqual(settings.max_retries, 3)

    def test_negative_zero_invalid_types_and_extreme_values_are_rejected(self) -> None:
        cases = {
            "CRAWLER_GLOBAL_CONCURRENCY": "0",
            "CRAWLER_DOMAIN_DELAY_SECONDS": "-1",
            "CRAWLER_CONNECT_TIMEOUT_SECONDS": "none",
            "CRAWLER_READ_TIMEOUT_SECONDS": "0",
            "CRAWLER_MAX_RESPONSE_BYTES": "9999999999",
            "CRAWLER_MAX_REDIRECTS": "0",
            "CRAWLER_MAX_DEPTH": "0",
            "CRAWLER_DNS_CACHE_SECONDS": "301",
            "CRAWLER_MAX_RETRIES": "0",
        }
        for key, value in cases.items():
            with self.subTest(key=key):
                with self.assertRaises(CrawlerConfigError):
                    CrawlerSettings.from_env({key: value})

    def test_user_agent_must_be_safe_and_nonblank(self) -> None:
        for value in ("", "bot\r\nInjected: yes", "x" * 256):
            with self.subTest(value=repr(value)):
                with self.assertRaises(CrawlerConfigError):
                    CrawlerSettings.from_env({"CRAWLER_USER_AGENT": value})


if __name__ == "__main__":
    unittest.main()
