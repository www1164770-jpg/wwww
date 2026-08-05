"""Explicit construction of the Phase 3 icon network safety stack."""

from __future__ import annotations

from backend.crawler.config import CrawlerSettings
from backend.crawler.fetch.http import PinnedIpTransport, StaticHttpFetcher, Transport
from backend.crawler.fetch.rate_limit import OriginRateLimiter
from backend.crawler.fetch.robots import RobotsCache
from backend.crawler.net.policy import NetworkPolicy, Resolver

from .download import IconDownloader


def build_icon_downloader(
    settings: CrawlerSettings,
    *,
    resolver: Resolver | None = None,
    transport: Transport | None = None,
) -> IconDownloader:
    network_policy = NetworkPolicy(
        resolver=resolver,
        cache_ttl_seconds=settings.dns_cache_seconds,
    )
    limiter = OriginRateLimiter(
        global_concurrency=settings.global_concurrency,
        default_delay_seconds=settings.domain_delay_seconds,
    )
    shared_transport = transport or PinnedIpTransport()
    robots_fetcher = StaticHttpFetcher(
        network_policy=network_policy,
        rate_limiter=limiter,
        transport=shared_transport,
        user_agent=settings.user_agent,
        connect_timeout_seconds=settings.connect_timeout_seconds,
        read_timeout_seconds=settings.read_timeout_seconds,
        max_response_bytes=min(settings.max_response_bytes, 512_000),
        max_redirects=settings.max_redirects,
        max_retries=settings.max_retries,
    )
    robots = RobotsCache(
        loader=robots_fetcher.fetch_robots,
        user_agent=settings.user_agent,
        ttl_seconds=settings.robots_cache_seconds,
    )
    return IconDownloader(
        network_policy=network_policy,
        rate_limiter=limiter,
        robots=robots,
        transport=shared_transport,
        user_agent=settings.user_agent,
        connect_timeout_seconds=settings.connect_timeout_seconds,
        read_timeout_seconds=settings.read_timeout_seconds,
        max_bytes=settings.icon_max_bytes,
        max_pixels=settings.icon_max_pixels,
        max_redirects=settings.icon_max_redirects,
    )


__all__ = ["build_icon_downloader"]
