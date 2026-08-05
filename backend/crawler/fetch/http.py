"""Bounded static HTTP GET client with mandatory DNS/SSRF checks."""

from __future__ import annotations

from dataclasses import dataclass
from email.utils import parsedate_to_datetime
import gzip
import ssl
import threading
import time
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit
import zlib
from typing import Protocol

import urllib3

from backend.crawler.errors import Cancelled, CrawlerError
from backend.crawler.net.policy import NetworkPolicy, ResolvedTarget
from backend.crawler.net.url import InvalidUrl, normalize_http_url

from .rate_limit import OriginRateLimiter
from .robots import RobotsDecision, RobotsResponse


_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "text/html",
        "application/xhtml+xml",
        "application/xml",
        "text/xml",
        "application/rss+xml",
        "application/atom+xml",
        "application/sitemap+xml",
        "application/gzip",
        "application/x-gzip",
    }
)
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


class ResponseLike(Protocol):
    status: int
    headers: Mapping[str, str]

    def read(self, amount: int) -> bytes: ...

    def close(self) -> None: ...


class Transport(Protocol):
    def request(
        self,
        target: ResolvedTarget,
        *,
        path: str,
        headers: Mapping[str, str],
        connect_timeout: float,
        read_timeout: float,
    ) -> ResponseLike: ...


class RobotsPolicy(Protocol):
    def check(
        self,
        url: str,
        *,
        cancel_event: threading.Event | None = None,
    ) -> RobotsDecision: ...


@dataclass(frozen=True, slots=True)
class HttpFetchResult:
    requested_url: str
    normalized_url: str
    final_url: str
    status_code: int
    content_type: str
    charset: str | None
    body: bytes
    bytes_read: int
    redirect_chain: tuple[str, ...]
    elapsed_ms: int
    etag: str | None
    last_modified: str | None
    robots: RobotsDecision | None


class PinnedIpTransport:
    """Reuse pools keyed by a policy-approved concrete address."""

    def __init__(self) -> None:
        self._pools: dict[tuple[str, str, int, str], object] = {}
        self._lock = threading.Lock()

    def _pool(self, target: ResolvedTarget):
        normalized = target.normalized_url
        address = target.addresses[0]
        key = (normalized.scheme, target.hostname, target.port, address)
        with self._lock:
            pool = self._pools.get(key)
            if pool is None:
                if normalized.scheme == "https":
                    pool = urllib3.HTTPSConnectionPool(
                        address,
                        port=target.port,
                        cert_reqs=ssl.CERT_REQUIRED,
                        assert_hostname=target.hostname,
                        server_hostname=target.hostname,
                        maxsize=4,
                        block=True,
                    )
                else:
                    pool = urllib3.HTTPConnectionPool(
                        address,
                        port=target.port,
                        maxsize=4,
                        block=True,
                    )
                self._pools[key] = pool
        return pool

    def request(
        self,
        target: ResolvedTarget,
        *,
        path: str,
        headers: Mapping[str, str],
        connect_timeout: float,
        read_timeout: float,
    ) -> ResponseLike:
        timeout = urllib3.Timeout(connect=connect_timeout, read=read_timeout)
        return self._pool(target).request(
            "GET",
            path,
            headers=dict(headers),
            timeout=timeout,
            redirect=False,
            preload_content=False,
            decode_content=False,
            retries=False,
        )

    def close(self) -> None:
        with self._lock:
            pools = tuple(self._pools.values())
            self._pools.clear()
        for pool in pools:
            pool.close()


def _headers(response: ResponseLike) -> dict[str, str]:
    return {str(key).lower(): str(value).strip() for key, value in response.headers.items()}


def _content_type(value: str | None) -> tuple[str, str | None]:
    if not value:
        return "", None
    parts = [part.strip() for part in value.split(";")]
    media_type = parts[0].lower()
    charset = None
    for parameter in parts[1:]:
        name, separator, raw_value = parameter.partition("=")
        if separator and name.strip().lower() == "charset":
            charset = raw_value.strip().strip("\"'")[:64] or None
    return media_type, charset


def _retry_after(value: str | None, now: Callable[[], datetime]) -> float | None:
    if not value:
        return None
    try:
        return min(max(float(value), 0.0), 300.0)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            current = now()
            if current.tzinfo is None:
                current = current.replace(tzinfo=timezone.utc)
            return min(max((parsed - current).total_seconds(), 0.0), 300.0)
        except (TypeError, ValueError, OverflowError):
            return None


class StaticHttpFetcher:
    def __init__(
        self,
        *,
        network_policy: NetworkPolicy,
        rate_limiter: OriginRateLimiter,
        user_agent: str,
        connect_timeout_seconds: float,
        read_timeout_seconds: float,
        max_response_bytes: int,
        max_redirects: int,
        max_retries: int,
        transport: Transport | None = None,
        robots: RobotsPolicy | None = None,
        wait: Callable[[threading.Event, float], bool] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        if not user_agent.strip():
            raise ValueError("crawler user agent must not be blank")
        if connect_timeout_seconds <= 0 or read_timeout_seconds <= 0:
            raise ValueError("crawler HTTP timeouts must be positive")
        if max_response_bytes < 1 or max_redirects < 0 or max_retries < 0:
            raise ValueError("crawler HTTP limits are invalid")
        self._network_policy = network_policy
        self._rate_limiter = rate_limiter
        self._user_agent = user_agent
        self._connect_timeout = float(connect_timeout_seconds)
        self._read_timeout = float(read_timeout_seconds)
        self._max_bytes = max_response_bytes
        self._max_redirects = max_redirects
        self._max_retries = max_retries
        self._transport = transport or PinnedIpTransport()
        self._robots = robots
        self._wait = wait or (lambda event, seconds: event.wait(seconds))
        self._monotonic = monotonic
        self._now = now or (lambda: datetime.now(timezone.utc))

    def set_robots_policy(self, robots: RobotsPolicy) -> None:
        self._robots = robots

    @staticmethod
    def _cancelled(event: threading.Event) -> None:
        if event.is_set():
            raise Cancelled()

    def _read_body(
        self,
        response: ResponseLike,
        headers: Mapping[str, str],
        *,
        check_content_type: bool,
        cancel_event: threading.Event,
    ) -> tuple[bytes, str, str | None]:
        media_type, charset = _content_type(headers.get("content-type"))
        if check_content_type and media_type not in _ALLOWED_CONTENT_TYPES:
            raise CrawlerError("unsupported_content_type", "response media type is not supported")
        length = headers.get("content-length")
        if length:
            try:
                if int(length) > self._max_bytes:
                    raise CrawlerError("response_too_large", "response exceeded byte limit")
            except ValueError:
                pass
        raw = bytearray()
        while True:
            self._cancelled(cancel_event)
            try:
                chunk = response.read(min(65_536, self._max_bytes + 1 - len(raw)))
            except TimeoutError as error:
                raise CrawlerError("read_timeout", "response read timed out", retryable=True) from error
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > self._max_bytes:
                raise CrawlerError("response_too_large", "response exceeded byte limit")
        encoding = headers.get("content-encoding", "").lower()
        try:
            if encoding == "gzip":
                decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
                body = decoder.decompress(bytes(raw), self._max_bytes + 1)
                if len(body) > self._max_bytes or decoder.unconsumed_tail:
                    raise CrawlerError("response_too_large", "decompressed response exceeded byte limit")
                body += decoder.flush(self._max_bytes + 1 - len(body))
            elif encoding == "deflate":
                try:
                    decoder = zlib.decompressobj()
                    body = decoder.decompress(bytes(raw), self._max_bytes + 1)
                    if len(body) > self._max_bytes or decoder.unconsumed_tail:
                        raise CrawlerError("response_too_large", "decompressed response exceeded byte limit")
                    body += decoder.flush(self._max_bytes + 1 - len(body))
                except zlib.error:
                    decoder = zlib.decompressobj(-zlib.MAX_WBITS)
                    body = decoder.decompress(bytes(raw), self._max_bytes + 1)
                    if len(body) > self._max_bytes or decoder.unconsumed_tail:
                        raise CrawlerError("response_too_large", "decompressed response exceeded byte limit")
                    body += decoder.flush(self._max_bytes + 1 - len(body))
            elif encoding in {"", "identity"}:
                body = bytes(raw)
            else:
                raise CrawlerError("unsupported_content_type", "response encoding is not supported")
        except (gzip.BadGzipFile, EOFError, zlib.error) as error:
            raise CrawlerError("http_4xx", "response compression is invalid") from error
        if len(body) > self._max_bytes:
            raise CrawlerError("response_too_large", "decompressed response exceeded byte limit")
        return body, media_type, charset

    def _transport_request(self, target: ResolvedTarget, event: threading.Event) -> ResponseLike:
        self._cancelled(event)
        parsed = urlsplit(target.normalized_url.url)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        host = target.hostname
        default_port = 443 if target.normalized_url.scheme == "https" else 80
        if target.port != default_port:
            host = f"{host}:{target.port}"
        headers = {
            "User-Agent": self._user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml,text/xml,application/rss+xml,application/atom+xml;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Host": host,
            "Connection": "keep-alive",
        }
        try:
            return self._transport.request(
                target,
                path=path,
                headers=headers,
                connect_timeout=self._connect_timeout,
                read_timeout=self._read_timeout,
            )
        except Cancelled:
            raise
        except ssl.SSLError as error:
            raise CrawlerError("tls_error", "TLS negotiation failed", retryable=True) from error
        except TimeoutError as error:
            raise CrawlerError("read_timeout", "response read timed out", retryable=True) from error
        except ConnectionError as error:
            raise CrawlerError("connect_timeout", "connection failed or timed out", retryable=True) from error
        except urllib3.exceptions.SSLError as error:
            raise CrawlerError("tls_error", "TLS negotiation failed", retryable=True) from error
        except urllib3.exceptions.ReadTimeoutError as error:
            raise CrawlerError("read_timeout", "response read timed out", retryable=True) from error
        except (urllib3.exceptions.ConnectTimeoutError, urllib3.exceptions.NewConnectionError) as error:
            raise CrawlerError("connect_timeout", "connection failed or timed out", retryable=True) from error
        except urllib3.exceptions.ProtocolError as error:
            raise CrawlerError("read_timeout", "connection ended during response", retryable=True) from error

    def _fetch(
        self,
        raw_url: str,
        *,
        cancel_event: threading.Event,
        obey_robots: bool,
        check_content_type: bool,
        raise_http_errors: bool,
    ) -> HttpFetchResult:
        started = self._monotonic()
        try:
            requested = normalize_http_url(raw_url)
        except InvalidUrl as error:
            raise CrawlerError("invalid_url", "crawler URL is invalid") from error
        current = requested
        visited = {current.url}
        redirect_chain: list[str] = []
        retry_count = 0
        final_robots: RobotsDecision | None = None

        while True:
            self._cancelled(cancel_event)
            target = self._network_policy.check_url(current, force_refresh=True)
            decision = None
            if obey_robots:
                if self._robots is None:
                    raise CrawlerError("robots_denied", "robots policy is unavailable", retryable=True)
                decision = self._robots.check(current.url, cancel_event=cancel_event)
                if not decision.allowed:
                    raise CrawlerError("robots_denied", "robots policy denied the target", http_status=decision.status_code)
                final_robots = decision

            response: ResponseLike | None = None
            retry = False
            with self._rate_limiter.slot(
                current.origin,
                crawl_delay=decision.crawl_delay if decision is not None else None,
                cancel_event=cancel_event,
            ):
                response = self._transport_request(target, cancel_event)
                try:
                    headers = _headers(response)
                    status = int(response.status)
                    if status in _RETRYABLE_STATUSES and retry_count < self._max_retries:
                        delay = _retry_after(headers.get("retry-after"), self._now)
                        if delay is None:
                            delay = min(0.5 * (2**retry_count), 30.0)
                        retry_count += 1
                        retry = True
                    elif 300 <= status < 400:
                        location = headers.get("location")
                        if not location:
                            raise CrawlerError("http_4xx", "redirect did not include a location", http_status=status)
                        if len(redirect_chain) >= self._max_redirects:
                            raise CrawlerError("redirect_limit", "redirect limit exceeded")
                        try:
                            next_url = normalize_http_url(urljoin(current.url, location))
                        except InvalidUrl as error:
                            raise CrawlerError("invalid_url", "redirect URL is invalid") from error
                        if next_url.url in visited:
                            raise CrawlerError("redirect_loop", "redirect loop detected")
                        visited.add(next_url.url)
                        redirect_chain.append(next_url.url)
                        current = next_url
                    else:
                        if raise_http_errors and 400 <= status < 500:
                            raise CrawlerError("http_4xx", "remote server returned a client error", http_status=status)
                        if raise_http_errors and status >= 500:
                            raise CrawlerError("http_5xx", "remote server returned a server error", retryable=True, http_status=status)
                        body, media_type, charset = self._read_body(
                            response,
                            headers,
                            check_content_type=check_content_type,
                            cancel_event=cancel_event,
                        )
                        return HttpFetchResult(
                            requested_url=requested.url,
                            normalized_url=requested.url,
                            final_url=current.url,
                            status_code=status,
                            content_type=media_type,
                            charset=charset,
                            body=body,
                            bytes_read=len(body),
                            redirect_chain=tuple(redirect_chain),
                            elapsed_ms=max(0, round((self._monotonic() - started) * 1000)),
                            etag=headers.get("etag"),
                            last_modified=headers.get("last-modified"),
                            robots=final_robots,
                        )
                finally:
                    response.close()
            if retry:
                if self._wait(cancel_event, delay):
                    raise Cancelled()
                continue
            if redirect_chain and current.url == redirect_chain[-1]:
                continue

    def fetch(
        self,
        url: str,
        *,
        cancel_event: threading.Event | None = None,
    ) -> HttpFetchResult:
        return self._fetch(
            url,
            cancel_event=cancel_event or threading.Event(),
            obey_robots=True,
            check_content_type=True,
            raise_http_errors=True,
        )

    def fetch_robots(
        self,
        url: str,
        cancel_event: threading.Event,
    ) -> RobotsResponse:
        result = self._fetch(
            url,
            cancel_event=cancel_event,
            obey_robots=False,
            check_content_type=False,
            raise_http_errors=False,
        )
        return RobotsResponse(result.status_code, result.body)

    def close(self) -> None:
        close = getattr(self._transport, "close", None)
        if close is not None:
            close()


_PinnedIpTransport = PinnedIpTransport


__all__ = ["HttpFetchResult", "PinnedIpTransport", "StaticHttpFetcher", "Transport"]
