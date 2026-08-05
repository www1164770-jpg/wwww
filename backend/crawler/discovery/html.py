"""Tolerant HTML metadata and link extraction without regular-expression parsing."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html.parser import HTMLParser
import json
import re
from urllib.parse import urljoin

from backend.crawler.net.url import InvalidUrl, normalize_http_url


_WHITESPACE = re.compile(r"\s+")
_HIDDEN = frozenset({"script", "style", "noscript", "template", "svg"})


def _clean(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    cleaned = _WHITESPACE.sub(" ", value).strip()
    return cleaned[:limit] or None


def _resolved(value: str | None, base_url: str) -> str | None:
    if not value:
        return None
    try:
        return normalize_http_url(urljoin(base_url, value.strip())).url
    except (InvalidUrl, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class HtmlLink:
    url: str
    relation_type: str
    discovery_type: str = "html_anchor"
    anchor_text: str | None = None


@dataclass(frozen=True, slots=True)
class HtmlDocument:
    title: str | None
    meta_description: str | None
    canonical_url: str | None
    og_title: str | None
    og_description: str | None
    og_image_url: str | None
    twitter_title: str | None
    twitter_description: str | None
    twitter_image_url: str | None
    favicon_url: str | None
    apple_touch_icon_url: str | None
    language: str | None
    charset: str | None
    heading: str | None
    text_excerpt: str
    content_hash: str
    feed_urls: tuple[str, ...]
    sitemap_urls: tuple[str, ...]
    links: tuple[HtmlLink, ...]


class _Extractor(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.language: str | None = None
        self.charset: str | None = None
        self.meta: dict[str, str] = {}
        self.canonical: str | None = None
        self.favicon: str | None = None
        self.apple_icon: str | None = None
        self.feed_urls: list[str] = []
        self.sitemap_urls: list[str] = []
        self.links: list[HtmlLink] = []
        self.visible_parts: list[str] = []
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self._hidden_depth = 0
        self._title_depth = 0
        self._h1_depth = 0
        self._first_h1_done = False
        self._anchor: tuple[str, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        values = {str(key).lower(): value for key, value in attrs if key}
        if tag in _HIDDEN:
            self._hidden_depth += 1
        if tag == "html" and self.language is None:
            self.language = _clean(values.get("lang"), 64)
        elif tag == "title":
            self._title_depth += 1
        elif tag == "h1":
            self._h1_depth += 1
        elif tag == "meta":
            if self.charset is None:
                self.charset = _clean(values.get("charset"), 64)
            key = (
                values.get("name")
                or values.get("property")
                or values.get("http-equiv")
                or ""
            ).strip().lower()
            content = values.get("content")
            if key and content is not None and key not in self.meta:
                self.meta[key] = content
            if self.charset is None and key == "content-type" and content:
                for parameter in content.split(";")[1:]:
                    name, separator, value = parameter.partition("=")
                    if separator and name.strip().lower() == "charset":
                        self.charset = _clean(value.strip(" \"'"), 64)
        elif tag == "link":
            href = _resolved(values.get("href"), self.base_url)
            rels = {item.lower() for item in (values.get("rel") or "").split()}
            media_type = (values.get("type") or "").lower()
            if href and "canonical" in rels and self.canonical is None:
                self.canonical = href
            if href and ({"icon", "shortcut"} & rels) and self.favicon is None:
                self.favicon = href
            if href and "apple-touch-icon" in rels and self.apple_icon is None:
                self.apple_icon = href
            if href and "alternate" in rels and media_type in {
                "application/rss+xml",
                "application/atom+xml",
            }:
                self.feed_urls.append(href)
            if href and ("sitemap" in rels or media_type == "application/sitemap+xml"):
                self.sitemap_urls.append(href)
        elif tag == "a":
            href = _resolved(values.get("href"), self.base_url)
            if href:
                self._anchor = (href, [])

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title" and self._title_depth:
            self._title_depth -= 1
        elif tag == "h1" and self._h1_depth:
            self._h1_depth -= 1
            if self._h1_depth == 0:
                self._first_h1_done = True
        elif tag == "a" and self._anchor is not None:
            href, parts = self._anchor
            self.links.append(HtmlLink(href, "anchor", anchor_text=_clean(" ".join(parts), 500)))
            self._anchor = None
        if tag in _HIDDEN and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._hidden_depth:
            return
        cleaned = _clean(data, 20_000)
        if not cleaned:
            return
        self.visible_parts.append(cleaned)
        if self._title_depth:
            self.title_parts.append(cleaned)
        if self._h1_depth and not self._first_h1_done:
            self.h1_parts.append(cleaned)
        if self._anchor is not None:
            self._anchor[1].append(cleaned)


def parse_html(
    html: str | bytes,
    *,
    final_url: str,
    charset: str | None = None,
) -> HtmlDocument:
    normalized_base = normalize_http_url(final_url).url
    if isinstance(html, bytes):
        encodings = [charset, "utf-8", "windows-1252"]
        text = ""
        for encoding in encodings:
            if not encoding:
                continue
            try:
                text = html.decode(encoding)
                break
            except (LookupError, UnicodeDecodeError):
                continue
        if not text:
            text = html.decode("utf-8", errors="replace")
    else:
        text = html
    extractor = _Extractor(normalized_base)
    try:
        extractor.feed(text)
        extractor.close()
    except Exception:
        pass

    visible = _clean(" ".join(extractor.visible_parts), 100_000) or ""
    excerpt = visible[:4000]
    title = _clean(" ".join(extractor.title_parts), 500)
    heading = _clean(" ".join(extractor.h1_parts), 1000)
    meta_description = _clean(extractor.meta.get("description"), 2000)
    og_title = _clean(extractor.meta.get("og:title"), 500)
    og_description = _clean(extractor.meta.get("og:description"), 2000)
    twitter_title = _clean(extractor.meta.get("twitter:title"), 500)
    twitter_description = _clean(extractor.meta.get("twitter:description"), 2000)
    og_image = _resolved(extractor.meta.get("og:image"), normalized_base)
    twitter_image = _resolved(extractor.meta.get("twitter:image"), normalized_base)
    hash_material = json.dumps(
        {
            "title": title,
            "description": meta_description,
            "heading": heading,
            "text": visible,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    deduped_links = {link.url: link for link in extractor.links}
    return HtmlDocument(
        title,
        meta_description,
        extractor.canonical,
        og_title,
        og_description,
        og_image,
        twitter_title,
        twitter_description,
        twitter_image,
        extractor.favicon,
        extractor.apple_icon,
        extractor.language,
        extractor.charset or charset,
        heading,
        excerpt,
        sha256(hash_material.encode("utf-8")).hexdigest(),
        tuple(dict.fromkeys(extractor.feed_urls)),
        tuple(dict.fromkeys(extractor.sitemap_urls)),
        tuple(deduped_links.values()),
    )
