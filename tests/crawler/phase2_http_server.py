"""Loopback-only HTTP fixture reached through an injected crawler transport."""

from __future__ import annotations

import gzip
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
import time
from urllib.parse import urlsplit

import urllib3


class PhaseTwoSite:
    def __init__(self) -> None:
        self.version = 1
        self.counts: dict[str, int] = {}
        self.lock = threading.Lock()

    def hit(self, path: str) -> int:
        with self.lock:
            self.counts[path] = self.counts.get(path, 0) + 1
            return self.counts[path]


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    @property
    def site(self) -> PhaseTwoSite:
        return self.server.site

    @property
    def origin(self) -> str:
        return self.server.public_origin

    def log_message(self, _format, *args) -> None:
        return

    def _send(self, status: int, body: bytes = b"", content_type: str = "text/html; charset=utf-8", headers=None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        count = self.site.hit(path)
        if path == "/robots.txt":
            body = f"""User-agent: ZhiHuiNavigationBot
Disallow: /blocked
Allow: /
Crawl-delay: 0.001
Sitemap: {self.origin}/sitemap-index.xml
""".encode()
            self._send(200, body, "text/plain; charset=utf-8")
        elif path == "/":
            body = f"""<!doctype html><html lang='zh-CN'><head>
            <meta charset='utf-8'><title>Seed v{self.site.version}</title>
            <meta name='description' content='Phase 2 seed'>
            <link rel='alternate' type='application/rss+xml' href='/feed.xml'>
            </head><body><h1>静态抓取 🚀</h1>
            <a href='/page-1?utm_source=test'>Page 1</a>
            <a href='/blocked'>Blocked</a>
            <a href='https://external.example/out'>External</a>
            </body></html>""".encode()
            self._send(200, body)
        elif path == "/page-1":
            self._send(200, b"<title>Page 1</title><a href='/page-2'>Page 2</a><a href='/redirect'>Redirect</a>")
        elif path == "/page-2":
            self._send(200, b"<title>Page 2</title><a href='/#fragment'>Home</a>")
        elif path == "/blocked":
            self._send(200, b"this must never be fetched")
        elif path == "/sitemap.xml":
            body = f"""<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
            <url><loc>{self.origin}/unicode</loc></url>
            <url><loc>{self.origin}/page-2</loc></url></urlset>""".encode()
            self._send(200, body, "application/xml")
        elif path == "/sitemap-index.xml":
            body = f"""<sitemapindex xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
            <sitemap><loc>{self.origin}/sitemap.xml</loc></sitemap>
            <sitemap><loc>{self.origin}/sitemap.xml.gz</loc></sitemap></sitemapindex>""".encode()
            self._send(200, body, "application/xml")
        elif path == "/sitemap.xml.gz":
            xml = f"""<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
            <url><loc>{self.origin}/gzip</loc></url></urlset>""".encode()
            self._send(200, gzip.compress(xml), "application/xml", {"Content-Encoding": "gzip"})
        elif path == "/feed.xml":
            body = f"""<rss version='2.0'><channel><title>Phase Feed</title><link>{self.origin}/</link>
            <item><title>Page two</title><link>{self.origin}/page-2</link></item>
            <item><title>External</title><link>https://external.example/feed-item</link></item>
            </channel></rss>""".encode()
            self._send(200, body, "application/rss+xml")
        elif path == "/redirect":
            self._send(302, headers={"Location": "/page-2"})
        elif path == "/redirect-loop":
            self._send(302, headers={"Location": "/redirect-loop-2"})
        elif path == "/redirect-loop-2":
            self._send(302, headers={"Location": "/redirect-loop"})
        elif path == "/large":
            self._send(200, b"x" * 16_384)
        elif path == "/gzip":
            self._send(200, gzip.compress(b"<title>gzip</title>"), "text/html", {"Content-Encoding": "gzip"})
        elif path == "/slow":
            time.sleep(0.2)
            self._send(200, b"<title>slow</title>")
        elif path == "/retry-after":
            if count == 1:
                self._send(429, b"retry", headers={"Retry-After": "0"})
            else:
                self._send(200, b"<title>retry ok</title>")
        elif path == "/flaky":
            if count == 1:
                self._send(500, b"temporary")
            else:
                self._send(200, b"<title>flaky ok</title>")
        elif path == "/binary":
            self._send(200, b"%PDF", "application/pdf")
        elif path == "/unicode":
            self._send(200, "<title>中文 日本語 😀</title>".encode())
        else:
            self._send(404, b"not found")


class _QuietThreadingHttpServer(ThreadingHTTPServer):
    def handle_error(self, _request, _client_address) -> None:
        return


class PhaseTwoHttpServer:
    def __init__(self) -> None:
        self.site = PhaseTwoSite()
        self.server = _QuietThreadingHttpServer(("127.0.0.1", 0), _Handler)
        self.origin = f"http://phase2.test:{self.server.server_port}"
        self.server.site = self.site
        self.server.public_origin = self.origin
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_exc):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class LocalOnlyTransport:
    """Test adapter: policy sees public fixture DNS, socket stays on loopback."""

    def __init__(self, port: int) -> None:
        self.pool = urllib3.HTTPConnectionPool("127.0.0.1", port=port, maxsize=8, block=True)

    def request(self, target, *, path, headers, connect_timeout, read_timeout):
        return self.pool.request(
            "GET",
            path,
            headers=dict(headers),
            timeout=urllib3.Timeout(connect=connect_timeout, read=read_timeout),
            redirect=False,
            preload_content=False,
            decode_content=False,
            retries=False,
        )

    def close(self) -> None:
        self.pool.close()
