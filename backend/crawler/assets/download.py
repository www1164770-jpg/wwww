"""SSRF-checked bounded icon downloader with per-redirect revalidation."""

from __future__ import annotations

import ssl
import threading
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import urllib3

from backend.crawler.errors import CrawlerError
from backend.crawler.fetch.http import PinnedIpTransport, Transport
from backend.crawler.fetch.rate_limit import OriginRateLimiter
from backend.crawler.fetch.robots import RobotsDecision
from backend.crawler.net.policy import NetworkPolicy
from backend.crawler.net.url import InvalidUrl, normalize_http_url

from .icons import IconValidationError, StoredIcon, store_icon


class IconDownloader:
    def __init__(
        self,
        *,
        network_policy: NetworkPolicy,
        user_agent: str,
        connect_timeout_seconds: float,
        read_timeout_seconds: float,
        max_bytes: int,
        max_pixels: int,
        max_redirects: int,
        rate_limiter: OriginRateLimiter,
        robots,
        transport: Transport | None = None,
    ) -> None:
        if not user_agent.strip():
            raise ValueError("icon user agent must not be blank")
        if connect_timeout_seconds <= 0 or read_timeout_seconds <= 0:
            raise ValueError("icon timeouts must be positive")
        if max_bytes < 1 or max_pixels < 1 or not 0 <= max_redirects <= 10:
            raise ValueError("icon limits are invalid")
        self._policy = network_policy
        self._user_agent = user_agent.strip()
        self._connect_timeout = float(connect_timeout_seconds)
        self._read_timeout = float(read_timeout_seconds)
        self._max_bytes = max_bytes
        self._max_pixels = max_pixels
        self._max_redirects = max_redirects
        self._rate_limiter = rate_limiter
        self._robots = robots
        self._transport = transport or PinnedIpTransport()

    def _request(self, target):
        parsed = urlsplit(target.normalized_url.url)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        host = target.hostname
        default_port = 443 if target.normalized_url.scheme == "https" else 80
        if target.port != default_port:
            host = f"{host}:{target.port}"
        try:
            return self._transport.request(
                target,
                path=path,
                headers={
                    "User-Agent": self._user_agent,
                    "Accept": "image/png,image/jpeg,image/gif,image/webp,image/x-icon",
                    "Accept-Encoding": "identity",
                    "Host": host,
                    "Connection": "keep-alive",
                },
                connect_timeout=self._connect_timeout,
                read_timeout=self._read_timeout,
            )
        except (TimeoutError, urllib3.exceptions.TimeoutError) as error:
            raise CrawlerError("icon_timeout", "icon request timed out", retryable=True) from error
        except (ConnectionError, OSError, ssl.SSLError, urllib3.exceptions.HTTPError) as error:
            raise CrawlerError("icon_unavailable", "icon request failed", retryable=True) from error

    def download(self, url: str, *, root: Path) -> StoredIcon:
        try:
            requested = normalize_http_url(url)
        except InvalidUrl as error:
            raise IconValidationError("invalid_icon_url") from error
        current = requested
        visited = {current.url}
        redirects = 0
        while True:
            target = self._policy.check_url(current, force_refresh=True)
            decision: RobotsDecision = self._robots.check(
                current.url,
                cancel_event=threading.Event(),
            )
            if not decision.allowed:
                raise CrawlerError("robots_denied", "robots policy denied the icon")
            with self._rate_limiter.slot(
                current.origin,
                crawl_delay=decision.crawl_delay,
                cancel_event=threading.Event(),
            ):
                response = self._request(target)
            try:
                headers = {str(key).lower(): str(value).strip() for key, value in response.headers.items()}
                status = int(response.status)
                if 300 <= status < 400:
                    location = headers.get("location")
                    if not location or redirects >= self._max_redirects:
                        raise IconValidationError("icon_redirect")
                    try:
                        next_url = normalize_http_url(urljoin(current.url, location))
                    except InvalidUrl as error:
                        raise IconValidationError("invalid_icon_url") from error
                    if next_url.url in visited:
                        raise IconValidationError("icon_redirect")
                    visited.add(next_url.url)
                    redirects += 1
                    current = next_url
                    continue
                if status != 200:
                    raise IconValidationError("icon_http_status")
                if headers.get("content-encoding", "identity").lower() not in {"", "identity"}:
                    raise IconValidationError("unsupported_image_encoding")
                content_length = headers.get("content-length")
                if content_length:
                    try:
                        if int(content_length) > self._max_bytes:
                            raise IconValidationError("image_too_large")
                    except ValueError:
                        pass
                body = bytearray()
                while True:
                    chunk = response.read(min(65_536, self._max_bytes + 1 - len(body)))
                    if not chunk:
                        break
                    body.extend(chunk)
                    if len(body) > self._max_bytes:
                        raise IconValidationError("image_too_large")
                return store_icon(
                    bytes(body),
                    declared_mime=headers.get("content-type", ""),
                    source_url=current.url,
                    root=root,
                    max_bytes=self._max_bytes,
                    max_pixels=self._max_pixels,
                )
            finally:
                response.close()

    def close(self) -> None:
        close = getattr(self._transport, "close", None)
        if close is not None:
            close()


__all__ = ["IconDownloader"]
