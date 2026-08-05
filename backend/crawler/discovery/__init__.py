"""Side-effect-free Phase 2 document parsing and link selection."""

from .feed import FeedDocument, parse_feed
from .html import HtmlDocument, HtmlLink, parse_html
from .links import DiscoveredCandidate, DiscoveryPolicy, select_discovered_links
from .sitemap import SitemapDocument, SitemapError, parse_sitemap

__all__ = [
    "DiscoveredCandidate",
    "DiscoveryPolicy",
    "FeedDocument",
    "HtmlDocument",
    "HtmlLink",
    "SitemapDocument",
    "SitemapError",
    "parse_feed",
    "parse_html",
    "parse_sitemap",
    "select_discovered_links",
]
