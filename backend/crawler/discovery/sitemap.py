"""Bounded, entity-safe Sitemap URL Set and Sitemap Index parsing."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import xml.etree.ElementTree as ET
import zlib

from backend.crawler.net.url import InvalidUrl, normalize_http_url, same_origin


class SitemapError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SitemapLocation:
    url: str
    same_origin: bool
    last_modified: str | None = None


@dataclass(frozen=True, slots=True)
class SitemapDocument:
    kind: str
    urls: tuple[SitemapLocation, ...]
    sitemaps: tuple[SitemapLocation, ...]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _bounded_gzip(body: bytes, max_bytes: int) -> bytes:
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    output = decoder.decompress(body, max_bytes + 1)
    if len(output) > max_bytes or decoder.unconsumed_tail:
        raise SitemapError("sitemap exceeds decompressed byte limit")
    output += decoder.flush(max_bytes + 1 - len(output))
    if len(output) > max_bytes:
        raise SitemapError("sitemap exceeds decompressed byte limit")
    return output


def parse_sitemap(
    body: bytes,
    *,
    source_url: str,
    max_bytes: int,
    max_urls: int,
) -> SitemapDocument:
    if max_bytes < 1 or max_urls < 1:
        raise ValueError("sitemap limits must be positive")
    if body.startswith(b"\x1f\x8b"):
        try:
            body = _bounded_gzip(body, max_bytes)
        except zlib.error as error:
            raise SitemapError("invalid gzip sitemap") from error
    if len(body) > max_bytes:
        raise SitemapError("sitemap exceeds byte limit")
    lowered = body.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise SitemapError("unsafe XML declarations are forbidden")
    source = normalize_http_url(source_url)
    urls: list[SitemapLocation] = []
    sitemaps: list[SitemapLocation] = []
    kind: str | None = None
    try:
        for event, element in ET.iterparse(BytesIO(body), events=("start", "end")):
            name = _local(element.tag)
            if event == "start" and kind is None:
                if name not in {"urlset", "sitemapindex"}:
                    raise SitemapError("XML document is not a sitemap")
                kind = "urlset" if name == "urlset" else "index"
            if event != "end" or name not in {"url", "sitemap"}:
                continue
            values = {_local(child.tag): (child.text or "").strip() for child in element}
            raw_location = values.get("loc", "")
            try:
                normalized = normalize_http_url(raw_location)
            except (InvalidUrl, ValueError):
                element.clear()
                continue
            location = SitemapLocation(
                normalized.url,
                same_origin(source, normalized),
                values.get("lastmod") or None,
            )
            collection = urls if name == "url" else sitemaps
            collection.append(location)
            if len(urls) + len(sitemaps) > max_urls:
                raise SitemapError("sitemap URL limit exceeded")
            element.clear()
    except ET.ParseError as error:
        raise SitemapError("malformed sitemap XML") from error
    if kind is None:
        raise SitemapError("empty sitemap XML")
    return SitemapDocument(kind, tuple(urls), tuple(sitemaps))
