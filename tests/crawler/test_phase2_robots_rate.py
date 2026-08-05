from __future__ import annotations

from datetime import datetime, timedelta
import threading
import unittest

from backend.crawler.errors import Cancelled
from backend.crawler.fetch.rate_limit import OriginRateLimiter
from backend.crawler.fetch.robots import RobotsCache, RobotsResponse


NOW = datetime(2026, 8, 1, 12, 0, 0)


class RobotsTests(unittest.TestCase):
    def test_user_agent_allow_disallow_delay_and_sitemap(self) -> None:
        calls = []

        def loader(url, cancel_event):
            calls.append(url)
            return RobotsResponse(
                200,
                b"""User-agent: *
Disallow: /private
Allow: /private/public
Crawl-delay: 2.5
Sitemap: https://example.com/sitemap.xml

User-agent: ZhiHuiNavigationBot
Disallow: /blocked
Allow: /blocked/allowed
Crawl-delay: 3
""",
            )

        cache = RobotsCache(
            loader=loader,
            user_agent="ZhiHuiNavigationBot/1.0",
            ttl_seconds=60,
            clock=lambda: NOW,
        )
        denied = cache.check("https://example.com/blocked")
        allowed = cache.check("https://example.com/blocked/allowed")

        self.assertFalse(denied.allowed)
        self.assertEqual(denied.matched_rule, "/blocked")
        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.crawl_delay, 3.0)
        self.assertEqual(
            allowed.sitemaps, ("https://example.com/sitemap.xml",)
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(allowed.checked_at, NOW)
        self.assertEqual(allowed.expires_at, NOW + timedelta(seconds=60))

    def test_status_and_failure_policy_is_conservative(self) -> None:
        cases = (
            (404, True, None),
            (401, False, "robots_http_401"),
            (403, False, "robots_http_403"),
            (429, False, "robots_http_429"),
            (500, False, "robots_http_5xx"),
        )
        for status, expected, error_code in cases:
            with self.subTest(status=status):
                cache = RobotsCache(
                    loader=lambda _url, _cancel: RobotsResponse(status, b""),
                    user_agent="ZhiHuiNavigationBot/1.0",
                    ttl_seconds=10,
                    clock=lambda: NOW,
                )
                decision = cache.check("https://example.com/page")
                self.assertEqual(decision.allowed, expected)
                self.assertEqual(decision.error_code, error_code)

        def timeout(_url, _cancel):
            raise TimeoutError("private detail")

        decision = RobotsCache(
            loader=timeout,
            user_agent="ZhiHuiNavigationBot/1.0",
            ttl_seconds=10,
            clock=lambda: NOW,
        ).check("https://example.com/page")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.error_code, "robots_network_failure")

    def test_cache_expiry_refetches(self) -> None:
        current = [NOW]
        calls = []
        cache = RobotsCache(
            loader=lambda url, _cancel: calls.append(url)
            or RobotsResponse(404, b""),
            user_agent="bot",
            ttl_seconds=10,
            clock=lambda: current[0],
        )
        cache.check("https://example.com/a")
        cache.check("https://example.com/b")
        current[0] += timedelta(seconds=11)
        cache.check("https://example.com/c")
        self.assertEqual(len(calls), 2)


class OriginRateLimiterTests(unittest.TestCase):
    def test_origin_delay_does_not_block_other_origin(self) -> None:
        clock = [0.0]
        waits = []

        def wait(event, seconds):
            waits.append(seconds)
            clock[0] += seconds
            return event.is_set()

        limiter = OriginRateLimiter(
            global_concurrency=2,
            default_delay_seconds=1,
            monotonic=lambda: clock[0],
            wait=wait,
        )
        with limiter.slot("https://a.example"):
            pass
        with limiter.slot("https://b.example"):
            pass
        self.assertEqual(waits, [])
        with limiter.slot("https://a.example", crawl_delay=2):
            pass
        self.assertEqual(waits, [2.0])

    def test_wait_is_cancellable(self) -> None:
        cancelled = threading.Event()
        limiter = OriginRateLimiter(
            global_concurrency=1,
            default_delay_seconds=1,
            monotonic=lambda: 0.0,
            wait=lambda event, _seconds: event.set() or True,
        )
        with limiter.slot("https://example.com"):
            pass
        with self.assertRaises(Cancelled):
            with limiter.slot("https://example.com", cancel_event=cancelled):
                pass


if __name__ == "__main__":
    unittest.main()
