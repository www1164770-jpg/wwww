"""Explicit construction of the static network stack for CLI workers."""

from __future__ import annotations

from backend.crawler.config import CrawlerSettings
from backend.crawler.fetch.http import StaticHttpFetcher, Transport
from backend.crawler.fetch.rate_limit import OriginRateLimiter
from backend.crawler.fetch.robots import RobotsCache
from backend.crawler.net.policy import NetworkPolicy, Resolver

from .static import StaticTaskHandler


def build_static_handler(
    settings: CrawlerSettings,
    *,
    resolver: Resolver | None = None,
    transport: Transport | None = None,
) -> StaticTaskHandler:
    """Create services only when a worker command explicitly starts."""

    network_policy = NetworkPolicy(
        resolver=resolver,
        cache_ttl_seconds=settings.dns_cache_seconds,
    )
    limiter = OriginRateLimiter(
        global_concurrency=settings.global_concurrency,
        default_delay_seconds=settings.domain_delay_seconds,
    )
    fetcher = StaticHttpFetcher(
        network_policy=network_policy,
        rate_limiter=limiter,
        transport=transport,
        user_agent=settings.user_agent,
        connect_timeout_seconds=settings.connect_timeout_seconds,
        read_timeout_seconds=settings.read_timeout_seconds,
        max_response_bytes=settings.max_response_bytes,
        max_redirects=settings.max_redirects,
        max_retries=settings.max_retries,
    )
    robots = RobotsCache(
        loader=fetcher.fetch_robots,
        user_agent=settings.user_agent,
        ttl_seconds=settings.robots_cache_seconds,
    )
    fetcher.set_robots_policy(robots)
    return StaticTaskHandler(fetcher=fetcher, settings=settings)


__all__ = ["build_static_handler"]
