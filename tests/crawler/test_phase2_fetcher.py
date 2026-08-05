from __future__ import annotations

from datetime import datetime
import gzip
from io import BytesIO
import ssl
import threading
import unittest
import zlib

from backend.crawler.errors import CrawlerError
from backend.crawler.fetch.http import StaticHttpFetcher
from backend.crawler.fetch.rate_limit import OriginRateLimiter
from backend.crawler.fetch.robots import RobotsDecision
from backend.crawler.net.policy import NetworkPolicy


class FakeResponse:
    def __init__(self, status, body=b"", headers=None, chunk_size=None):
        self.status = status
        self.headers = headers or {}
        self._body = BytesIO(body)
        self._chunk_size = chunk_size
        self.closed = False

    def read(self, amount):
        return self._body.read(min(amount, self._chunk_size or amount))

    def close(self):
        self.closed = True


class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, target, **kwargs):
        self.calls.append((target.normalized_url.url, target.addresses, kwargs))
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class AllowRobots:
    def __init__(self):
        self.urls = []

    def check(self, url, *, cancel_event=None):
        self.urls.append(url)
        now = datetime(2026, 8, 1)
        return RobotsDecision(True, 200, None, (), now, now)


def make_fetcher(responses, *, max_bytes=100, max_redirects=3, retries=2, resolver=None, waits=None):
    transport = FakeTransport(responses)
    robots = AllowRobots()
    fetcher = StaticHttpFetcher(
        network_policy=NetworkPolicy(
            resolver=resolver or (lambda _host, _port: ["93.184.216.34"])
        ),
        transport=transport,
        robots=robots,
        rate_limiter=OriginRateLimiter(
            global_concurrency=2,
            default_delay_seconds=0.001,
        ),
        user_agent="ZhiHuiNavigationBot/1.0",
        connect_timeout_seconds=1,
        read_timeout_seconds=1,
        max_response_bytes=max_bytes,
        max_redirects=max_redirects,
        max_retries=retries,
        wait=(lambda event, seconds: waits.append(seconds) or False)
        if waits is not None
        else (lambda _event, _seconds: False),
    )
    return fetcher, transport, robots


class StaticHttpFetcherTests(unittest.TestCase):
    def test_html_charset_chunking_and_response_close(self) -> None:
        response = FakeResponse(
            200,
            "你好".encode("gb18030"),
            {"Content-Type": "text/html; charset=gb18030"},
            chunk_size=1,
        )
        fetcher, transport, robots = make_fetcher([response])
        result = fetcher.fetch("https://example.com")

        self.assertEqual(result.body.decode(result.charset), "你好")
        self.assertEqual(result.content_type, "text/html")
        self.assertEqual(result.bytes_read, 4)
        self.assertTrue(response.closed)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(robots.urls, ["https://example.com/"])

    def test_gzip_and_deflate_have_decompressed_limits(self) -> None:
        for encoding, encoded in (
            ("gzip", gzip.compress(b"hello")),
            ("deflate", zlib.compress(b"hello")),
        ):
            with self.subTest(encoding=encoding):
                response = FakeResponse(
                    200,
                    encoded,
                    {
                        "Content-Type": "application/xml",
                        "Content-Encoding": encoding,
                    },
                )
                fetcher, _transport, _robots = make_fetcher([response])
                self.assertEqual(fetcher.fetch("https://example.com/a").body, b"hello")

        oversized = FakeResponse(
            200,
            gzip.compress(b"x" * 101),
            {"Content-Type": "text/html", "Content-Encoding": "gzip"},
        )
        fetcher, _transport, _robots = make_fetcher([oversized], max_bytes=100)
        with self.assertRaises(CrawlerError) as caught:
            fetcher.fetch("https://example.com/")
        self.assertEqual(caught.exception.code, "response_too_large")
        self.assertTrue(oversized.closed)

    def test_content_length_stream_limit_and_unsupported_type(self) -> None:
        cases = (
            (
                FakeResponse(200, b"x", {"Content-Type": "text/html", "Content-Length": "101"}),
                "response_too_large",
            ),
            (FakeResponse(200, b"x" * 101, {"Content-Type": "text/html"}, 7), "response_too_large"),
            (FakeResponse(200, b"pdf", {"Content-Type": "application/pdf"}), "unsupported_content_type"),
        )
        for response, code in cases:
            with self.subTest(code=code):
                fetcher, _transport, _robots = make_fetcher([response])
                with self.assertRaises(CrawlerError) as caught:
                    fetcher.fetch("https://example.com/a")
                self.assertEqual(caught.exception.code, code)
                self.assertTrue(response.closed)

    def test_manual_redirect_rechecks_dns_robots_and_detects_loop_and_limit(self) -> None:
        first = FakeResponse(302, headers={"Location": "/next"})
        final = FakeResponse(200, b"ok", {"Content-Type": "text/html"})
        fetcher, transport, robots = make_fetcher([first, final])
        result = fetcher.fetch("https://example.com/start")
        self.assertEqual(result.final_url, "https://example.com/next")
        self.assertEqual(result.redirect_chain, ("https://example.com/next",))
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(len(robots.urls), 2)

        loop = [
            FakeResponse(302, headers={"Location": "/b"}),
            FakeResponse(302, headers={"Location": "/a"}),
        ]
        fetcher, _transport, _robots = make_fetcher(loop)
        with self.assertRaises(CrawlerError) as caught:
            fetcher.fetch("https://example.com/a")
        self.assertEqual(caught.exception.code, "redirect_loop")

        redirects = [
            FakeResponse(302, headers={"Location": f"/{index + 1}"})
            for index in range(3)
        ]
        fetcher, _transport, _robots = make_fetcher(redirects, max_redirects=2)
        with self.assertRaises(CrawlerError) as caught:
            fetcher.fetch("https://example.com/0")
        self.assertEqual(caught.exception.code, "redirect_limit")

    def test_redirect_to_private_or_non_http_is_rejected(self) -> None:
        def resolver(host, _port):
            return ["10.0.0.1"] if host == "internal.example" else ["93.184.216.34"]

        for location, expected in (
            ("http://internal.example/", "unsafe_target"),
            ("file:///secret", "invalid_url"),
        ):
            with self.subTest(location=location):
                response = FakeResponse(302, headers={"Location": location})
                fetcher, _transport, _robots = make_fetcher([response], resolver=resolver)
                with self.assertRaises(CrawlerError) as caught:
                    fetcher.fetch("https://example.com/")
                self.assertEqual(caught.exception.code, expected)

    def test_retry_after_retryable_status_and_error_classification(self) -> None:
        waits = []
        retry = FakeResponse(429, headers={"Retry-After": "2"})
        success = FakeResponse(200, b"ok", {"Content-Type": "text/html"})
        fetcher, _transport, _robots = make_fetcher([retry, success], waits=waits)
        self.assertEqual(fetcher.fetch("https://example.com/").body, b"ok")
        self.assertEqual(waits, [2.0])
        self.assertTrue(retry.closed)

        responses = [FakeResponse(500), FakeResponse(502), FakeResponse(503)]
        fetcher, _transport, _robots = make_fetcher(responses, retries=2, waits=[])
        with self.assertRaises(CrawlerError) as caught:
            fetcher.fetch("https://example.com/")
        self.assertEqual(caught.exception.code, "http_5xx")
        self.assertTrue(caught.exception.retryable)

    def test_timeout_tls_http_and_cancel_are_classified(self) -> None:
        for error, expected in (
            (ConnectionError("connect timeout"), "connect_timeout"),
            (TimeoutError("read timeout"), "read_timeout"),
            (ssl.SSLError("tls"), "tls_error"),
        ):
            with self.subTest(expected=expected):
                fetcher, _transport, _robots = make_fetcher([error])
                with self.assertRaises(CrawlerError) as caught:
                    fetcher.fetch("https://example.com/")
                self.assertEqual(caught.exception.code, expected)

        response = FakeResponse(404, b"no", {"Content-Type": "text/html"})
        fetcher, _transport, _robots = make_fetcher([response])
        with self.assertRaises(CrawlerError) as caught:
            fetcher.fetch("https://example.com/")
        self.assertEqual(caught.exception.code, "http_4xx")

        event = threading.Event()
        event.set()
        fetcher, transport, _robots = make_fetcher([])
        with self.assertRaises(CrawlerError) as caught:
            fetcher.fetch("https://example.com/", cancel_event=event)
        self.assertEqual(caught.exception.code, "cancelled")
        self.assertEqual(transport.calls, [])


if __name__ == "__main__":
    unittest.main()
