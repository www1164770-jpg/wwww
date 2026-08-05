from __future__ import annotations

import gzip
import unittest

from backend.crawler.discovery.html import parse_html
from backend.crawler.discovery.links import DiscoveryPolicy, select_discovered_links
from backend.crawler.discovery.sitemap import SitemapError, parse_sitemap
from backend.crawler.discovery.feed import parse_feed


class HtmlParserTests(unittest.TestCase):
    def test_metadata_visible_text_relative_urls_and_hash(self) -> None:
        html = """<!doctype html><html lang="zh-CN"><head>
        <meta charset="utf-8"><title>  Crawler   Home </title>
        <meta name="description" content="A useful page">
        <meta property="og:title" content="OG title">
        <meta property="og:description" content="OG desc">
        <meta property="og:image" content="/og.png">
        <meta name="twitter:title" content="Tw title">
        <meta name="twitter:description" content="Tw desc">
        <meta name="twitter:image" content="/tw.png">
        <link rel="canonical" href="/canonical?utm_source=x">
        <link rel="icon" href="/favicon.ico">
        <link rel="apple-touch-icon" href="/apple.png">
        <link rel="alternate" type="application/rss+xml" href="/feed.xml">
        <link rel="sitemap" href="/sitemap.xml">
        <style>hidden css</style><script>hidden script</script></head>
        <body><h1>Main heading</h1><p>Hello   世界</p>
        <noscript>hidden</noscript><template>hidden</template><svg><text>hidden</text></svg>
        <a href="/page-1#part">one</a><a href="https://other.example/x">external</a>
        <a href="mailto:a@example.com">mail</a></body></html>"""
        parsed = parse_html(html, final_url="https://example.com/base")

        self.assertEqual(parsed.title, "Crawler Home")
        self.assertEqual(parsed.meta_description, "A useful page")
        self.assertEqual(parsed.canonical_url, "https://example.com/canonical")
        self.assertEqual(parsed.og_image_url, "https://example.com/og.png")
        self.assertEqual(parsed.twitter_image_url, "https://example.com/tw.png")
        self.assertEqual(parsed.favicon_url, "https://example.com/favicon.ico")
        self.assertEqual(parsed.apple_touch_icon_url, "https://example.com/apple.png")
        self.assertEqual(parsed.language, "zh-CN")
        self.assertEqual(parsed.charset, "utf-8")
        self.assertEqual(parsed.heading, "Main heading")
        self.assertIn("Hello 世界", parsed.text_excerpt)
        self.assertNotIn("hidden", parsed.text_excerpt)
        self.assertEqual(parsed.feed_urls, ("https://example.com/feed.xml",))
        self.assertEqual(parsed.sitemap_urls, ("https://example.com/sitemap.xml",))
        self.assertEqual(
            {link.url for link in parsed.links},
            {"https://example.com/page-1", "https://other.example/x"},
        )
        self.assertEqual(parsed.content_hash, parse_html(html, final_url="https://example.com/base").content_hash)

    def test_malformed_empty_and_field_limits_are_isolated(self) -> None:
        parsed = parse_html(
            "<html><head><title>" + ("x" * 1000) + "</title></head><body><h1>hello",
            final_url="https://example.com/",
        )
        self.assertEqual(len(parsed.title), 500)
        self.assertEqual(parsed.heading, "hello")
        empty = parse_html("", final_url="https://example.com/")
        self.assertIsNone(empty.title)
        self.assertEqual(len(empty.content_hash), 64)


class DiscoveryPolicyTests(unittest.TestCase):
    def test_same_origin_recursion_limits_and_external_recording(self) -> None:
        parsed = parse_html(
            """<a href='/ok'>ok</a><a href='/login'>login</a>
            <a href='/report.pdf'>pdf</a><a href='https://other.example/x'>out</a>""",
            final_url="https://example.com/",
        )
        selected = select_discovered_links(
            parsed.links,
            source_url="https://example.com/",
            depth=0,
            policy=DiscoveryPolicy(max_depth=2, max_links_per_page=3),
        )
        by_url = {item.normalized_url: item for item in selected}
        self.assertTrue(by_url["https://example.com/ok"].enqueue)
        self.assertFalse(by_url["https://other.example/x"].enqueue)
        self.assertNotIn("https://example.com/login", by_url)
        self.assertNotIn("https://example.com/report.pdf", by_url)

        at_limit = select_discovered_links(
            parsed.links,
            source_url="https://example.com/",
            depth=2,
            policy=DiscoveryPolicy(max_depth=2, max_links_per_page=200),
        )
        self.assertFalse(any(item.enqueue for item in at_limit))


class SitemapParserTests(unittest.TestCase):
    def test_urlset_index_gzip_limits_and_external_entries(self) -> None:
        urlset = b"""<?xml version='1.0'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
          <url><loc>https://example.com/a</loc><lastmod>2026-01-01</lastmod></url>
          <url><loc>https://other.example/b</loc></url></urlset>"""
        parsed = parse_sitemap(gzip.compress(urlset), source_url="https://example.com/sitemap.xml", max_bytes=1000, max_urls=10)
        self.assertEqual(parsed.kind, "urlset")
        self.assertEqual(len(parsed.urls), 2)
        self.assertTrue(parsed.urls[0].same_origin)
        self.assertFalse(parsed.urls[1].same_origin)
        self.assertEqual(parsed.urls[0].last_modified, "2026-01-01")

        index = b"""<sitemapindex xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
          <sitemap><loc>https://example.com/child.xml</loc></sitemap>
          <sitemap><loc>https://outside.example/child.xml</loc></sitemap></sitemapindex>"""
        parsed_index = parse_sitemap(index, source_url="https://example.com/index.xml", max_bytes=1000, max_urls=10)
        self.assertEqual(parsed_index.kind, "index")
        self.assertEqual(len(parsed_index.sitemaps), 2)
        self.assertFalse(parsed_index.sitemaps[1].same_origin)

        with self.assertRaises(SitemapError):
            parse_sitemap(urlset, source_url="https://example.com/s.xml", max_bytes=20, max_urls=10)
        with self.assertRaises(SitemapError):
            parse_sitemap(urlset, source_url="https://example.com/s.xml", max_bytes=1000, max_urls=1)

    def test_xml_entity_attack_is_rejected(self) -> None:
        attack = b"<!DOCTYPE x [<!ENTITY e SYSTEM 'file:///etc/passwd'>]><urlset><url><loc>&e;</loc></url></urlset>"
        with self.assertRaises(SitemapError):
            parse_sitemap(attack, source_url="https://example.com/s.xml", max_bytes=1000, max_urls=10)


class FeedParserTests(unittest.TestCase):
    def test_rss_atom_relative_links_limits_and_malformed(self) -> None:
        rss = b"""<rss version='2.0'><channel><title>Feed</title><link>https://example.com/</link>
        <item><title>One</title><link>/one</link><pubDate>Tue, 01 Jul 2025 10:00:00 GMT</pubDate></item>
        <item><title>Two</title><link>https://other.example/two</link></item></channel></rss>"""
        parsed = parse_feed(rss, source_url="https://example.com/feed.xml", max_entries=1)
        self.assertEqual(parsed.title, "Feed")
        self.assertEqual(parsed.site_link, "https://example.com/")
        self.assertEqual(len(parsed.entries), 1)
        self.assertEqual(parsed.entries[0].link, "https://example.com/one")
        self.assertTrue(parsed.entries[0].same_origin)

        atom = b"""<feed xmlns='http://www.w3.org/2005/Atom'><title>Atom</title>
        <link href='https://example.com/'/><entry><title>Entry</title>
        <link href='/entry'/><updated>2026-08-01T00:00:00Z</updated></entry></feed>"""
        self.assertEqual(parse_feed(atom, source_url="https://example.com/a.xml", max_entries=10).entries[0].link, "https://example.com/entry")
        malformed = parse_feed(b"<rss><broken", source_url="https://example.com/b.xml", max_entries=10)
        self.assertIsNotNone(malformed.parse_error)

        entity = b"<!DOCTYPE x [<!ENTITY e SYSTEM 'http://evil/'>]><rss><channel><title>&e;</title></channel></rss>"
        self.assertEqual(parse_feed(entity, source_url="https://example.com/e.xml", max_entries=10).parse_error, "unsafe_xml")


if __name__ == "__main__":
    unittest.main()
