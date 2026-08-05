"""DNS-aware SSRF policy shared by every crawler network request."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import socket
import threading
import time
from collections.abc import Callable, Iterable

from backend.crawler.errors import CrawlerError

from .url import NormalizedUrl, normalize_http_url


Resolver = Callable[[str, int], Iterable[str]]


class UnsafeTarget(CrawlerError):
    def __init__(self, message: str = "target is not publicly routable") -> None:
        super().__init__("unsafe_target", message)


class DnsFailure(CrawlerError):
    def __init__(self, message: str = "target DNS resolution failed") -> None:
        super().__init__("dns_failure", message, retryable=True)


@dataclass(frozen=True, slots=True)
class ResolvedTarget:
    normalized_url: NormalizedUrl
    hostname: str
    port: int
    addresses: tuple[str, ...]
    checked_at: float


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    addresses: tuple[str, ...]
    expires_at: float


_METADATA_HOSTNAMES = frozenset(
    {
        "metadata",
        "metadata.google.internal",
        "metadata.azure.com",
        "instance-data",
        "instance-data.ec2.internal",
    }
)


def _system_resolver(hostname: str, port: int) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                item[4][0]
                for item in socket.getaddrinfo(
                    hostname,
                    port,
                    type=socket.SOCK_STREAM,
                )
            }
        )
    )


def _validated_ip(value: str) -> str:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as error:
        raise DnsFailure("resolver returned an invalid address") from error
    effective = address.ipv4_mapped if isinstance(address, ipaddress.IPv6Address) else None
    if effective is None:
        effective = address
    if (
        not effective.is_global
        or effective.is_private
        or effective.is_loopback
        or effective.is_link_local
        or effective.is_multicast
        or effective.is_reserved
        or effective.is_unspecified
    ):
        raise UnsafeTarget()
    return address.compressed


class NetworkPolicy:
    def __init__(
        self,
        *,
        resolver: Resolver | None = None,
        cache_ttl_seconds: int | float = 60,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if not 0 < cache_ttl_seconds <= 300:
            raise ValueError("DNS cache TTL must be between 0 and 300 seconds")
        self._resolver = resolver or _system_resolver
        self._cache_ttl = float(cache_ttl_seconds)
        self._monotonic = monotonic
        self._cache: dict[tuple[str, int], _CacheEntry] = {}
        self._lock = threading.Lock()

    def check_url(
        self,
        url: str | NormalizedUrl,
        *,
        force_refresh: bool = False,
    ) -> ResolvedTarget:
        normalized = normalize_http_url(url) if isinstance(url, str) else url
        hostname = normalized.hostname.lower().rstrip(".")
        if (
            hostname == "localhost"
            or hostname.endswith(".localhost")
            or hostname in _METADATA_HOSTNAMES
        ):
            raise UnsafeTarget()
        port = normalized.port or (443 if normalized.scheme == "https" else 80)
        key = (hostname, port)
        now = self._monotonic()

        if not force_refresh:
            with self._lock:
                cached = self._cache.get(key)
            if cached is not None and cached.expires_at > now:
                return ResolvedTarget(
                    normalized,
                    hostname,
                    port,
                    cached.addresses,
                    now,
                )

        try:
            literal = ipaddress.ip_address(hostname)
            raw_addresses = (literal.compressed,)
        except ValueError:
            try:
                raw_addresses = tuple(self._resolver(hostname, port))
            except (OSError, RuntimeError, ValueError) as error:
                raise DnsFailure() from error
        if not raw_addresses:
            raise DnsFailure("target DNS returned no addresses")
        addresses = tuple(sorted({_validated_ip(item) for item in raw_addresses}))
        with self._lock:
            self._cache[key] = _CacheEntry(addresses, now + self._cache_ttl)
        return ResolvedTarget(normalized, hostname, port, addresses, now)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
