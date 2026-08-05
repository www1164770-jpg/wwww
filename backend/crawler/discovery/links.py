"""Bounded same-origin discovery policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from backend.crawler.net.url import normalize_http_url, same_origin

from .html import HtmlLink


_EXCLUDED_SEGMENTS = frozenset(
    {"login", "signin", "sign-in", "signup", "sign-up", "register", "logout", "cart", "admin"}
)
_DOWNLOAD_EXTENSIONS = frozenset(
    {".pdf", ".zip", ".rar", ".7z", ".exe", ".msi", ".apk", ".dmg", ".iso", ".jpg", ".jpeg", ".png", ".gif", ".mp3", ".mp4"}
)


@dataclass(frozen=True, slots=True)
class DiscoveryPolicy:
    max_depth: int = 2
    max_links_per_page: int = 200
    same_origin_only: bool = True

    def __post_init__(self) -> None:
        if self.max_depth < 0 or not 1 <= self.max_links_per_page <= 10_000:
            raise ValueError("invalid link discovery limits")


@dataclass(frozen=True, slots=True)
class DiscoveredCandidate:
    discovered_url: str
    normalized_url: str
    relation_type: str
    discovery_type: str
    depth: int
    same_origin: bool
    enqueue: bool
    metadata: dict[str, str]


def _excluded(url: str) -> bool:
    path = urlsplit(url).path
    segments = {segment.lower() for segment in path.split("/") if segment}
    if segments & _EXCLUDED_SEGMENTS:
        return True
    return PurePosixPath(path.lower()).suffix in _DOWNLOAD_EXTENSIONS


def select_discovered_links(
    links: tuple[HtmlLink, ...],
    *,
    source_url: str,
    depth: int,
    policy: DiscoveryPolicy,
) -> tuple[DiscoveredCandidate, ...]:
    source = normalize_http_url(source_url)
    selected: list[DiscoveredCandidate] = []
    seen: set[str] = set()
    for link in links:
        normalized = normalize_http_url(link.url)
        if normalized.url in seen or _excluded(normalized.url):
            continue
        seen.add(normalized.url)
        internal = same_origin(source, normalized)
        next_depth = depth + 1
        selected.append(
            DiscoveredCandidate(
                discovered_url=link.url,
                normalized_url=normalized.url,
                relation_type=link.relation_type,
                discovery_type=link.discovery_type,
                depth=next_depth,
                same_origin=internal,
                enqueue=internal and next_depth <= policy.max_depth,
                metadata={"anchor_text": link.anchor_text} if link.anchor_text else {},
            )
        )
        if len(selected) >= policy.max_links_per_page:
            break
    return tuple(selected)
