"""Bounded RSS and Atom metadata extraction."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin

import feedparser

from backend.crawler.net.url import InvalidUrl, normalize_http_url, same_origin


@dataclass(frozen=True, slots=True)
class FeedEntry:
    title: str | None
    link: str
    published: str | None
    updated: str | None
    same_origin: bool


@dataclass(frozen=True, slots=True)
class FeedDocument:
    title: str | None
    site_link: str | None
    entries: tuple[FeedEntry, ...]
    parse_error: str | None = None


def _text(value, limit: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split()).strip()
    return cleaned[:limit] or None


def _url(value, source_url: str) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return normalize_http_url(urljoin(source_url, value)).url
    except (InvalidUrl, ValueError):
        return None


def parse_feed(body: bytes, *, source_url: str, max_entries: int) -> FeedDocument:
    if max_entries < 1:
        raise ValueError("feed entry limit must be positive")
    lowered = body.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        return FeedDocument(None, None, (), "unsafe_xml")
    source = normalize_http_url(source_url)
    parsed = feedparser.parse(body, resolve_relative_uris=False, sanitize_html=True)
    site_link = _url(parsed.feed.get("link"), source.url)
    entries: list[FeedEntry] = []
    for item in parsed.entries[:max_entries]:
        link = _url(item.get("link"), source.url)
        if link is None:
            continue
        entries.append(
            FeedEntry(
                _text(item.get("title"), 500),
                link,
                _text(item["published"] if "published" in item else None, 128),
                _text(item["updated"] if "updated" in item else None, 128),
                same_origin(source, normalize_http_url(link)),
            )
        )
    error = "malformed_feed" if getattr(parsed, "bozo", False) else None
    return FeedDocument(
        _text(parsed.feed.get("title"), 500),
        site_link,
        tuple(entries),
        error,
    )
