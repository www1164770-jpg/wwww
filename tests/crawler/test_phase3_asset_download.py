from __future__ import annotations

from io import BytesIO
from pathlib import Path
import struct
import tempfile
import unittest

from backend.crawler.assets.download import IconDownloader
from backend.crawler.fetch.rate_limit import OriginRateLimiter
from backend.crawler.fetch.robots import RobotsDecision
from backend.crawler.net.policy import NetworkPolicy, UnsafeTarget
from tests.crawler.support import NOW


def png() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
        + struct.pack(">II", 16, 16) + b"\x08\x06\x00\x00\x00"
        + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )


class Response:
    def __init__(self, status, body=b"", headers=None):
        self.status = status
        self.headers = headers or {}
        self._body = BytesIO(body)
        self.closed = False

    def read(self, amount):
        return self._body.read(amount)

    def close(self):
        self.closed = True


class Transport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, target, **kwargs):
        self.calls.append((target.hostname, target.addresses, kwargs))
        return self.responses.pop(0)


class AllowRobots:
    def check(self, _url, *, cancel_event=None):
        return RobotsDecision(True, 200, None, (), NOW, NOW)


def limiter():
    return OriginRateLimiter(global_concurrency=1, default_delay_seconds=0.001)


class PhaseThreeIconDownloadTests(unittest.TestCase):
    def test_download_revalidates_redirect_and_stores_valid_icon(self) -> None:
        response = Response(200, png(), {"Content-Type": "image/png"})
        transport = Transport([response])
        downloader = IconDownloader(
            network_policy=NetworkPolicy(resolver=lambda _host, _port: ["93.184.216.34"]),
            transport=transport,
            user_agent="ZhiHuiNavigationBot/1.0",
            connect_timeout_seconds=1,
            read_timeout_seconds=1,
            max_bytes=1024,
            max_pixels=1_000_000,
            max_redirects=2,
            rate_limiter=limiter(),
            robots=AllowRobots(),
        )
        with tempfile.TemporaryDirectory() as directory:
            stored = downloader.download(
                "https://example.com/favicon.png?secret=value",
                root=Path(directory),
            )
            self.assertTrue((Path(directory) / stored.relative_path).is_file())
            self.assertNotIn("secret=value", stored.source_url)
        self.assertTrue(response.closed)
        self.assertEqual(len(transport.calls), 1)

    def test_redirect_to_private_target_is_rejected_before_second_request(self) -> None:
        redirect = Response(302, headers={"Location": "http://internal.example/icon.png"})
        transport = Transport([redirect])

        def resolver(host, _port):
            return ["10.0.0.1"] if host == "internal.example" else ["93.184.216.34"]

        downloader = IconDownloader(
            network_policy=NetworkPolicy(resolver=resolver),
            transport=transport,
            user_agent="ZhiHuiNavigationBot/1.0",
            connect_timeout_seconds=1,
            read_timeout_seconds=1,
            max_bytes=1024,
            max_pixels=1_000_000,
            max_redirects=2,
            rate_limiter=limiter(),
            robots=AllowRobots(),
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(UnsafeTarget):
                downloader.download("https://example.com/favicon.png", root=Path(directory))
        self.assertEqual(len(transport.calls), 1)
        self.assertTrue(redirect.closed)


if __name__ == "__main__":
    unittest.main()
