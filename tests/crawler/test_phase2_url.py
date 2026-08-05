from __future__ import annotations

import unittest

from backend.crawler.net.url import (
    InvalidUrl,
    normalize_http_url,
    same_origin,
)


class PhaseTwoUrlNormalizationTests(unittest.TestCase):
    def test_normalizes_http_https_idn_fragment_port_and_query(self) -> None:
        normalized = normalize_http_url(
            " HTTPS://B\u00dcCHER.example:443/a/../path?z=2&utm_source=x&a=3&a=1#part "
        )

        self.assertEqual(
            normalized.url,
            "https://xn--bcher-kva.example/path?a=1&a=3&z=2",
        )
        self.assertEqual(normalized.scheme, "https")
        self.assertEqual(normalized.hostname, "xn--bcher-kva.example")
        self.assertEqual(normalized.origin, "https://xn--bcher-kva.example")
        self.assertEqual(len(normalized.fingerprint), 64)
        self.assertEqual(
            normalized.fingerprint,
            normalize_http_url(normalized.url).fingerprint,
        )

    def test_empty_path_default_ports_and_punycode_are_stable(self) -> None:
        self.assertEqual(
            normalize_http_url("http://Example.COM:80").url,
            "http://example.com/",
        )
        self.assertEqual(
            normalize_http_url("https://xn--bcher-kva.example/").url,
            "https://xn--bcher-kva.example/",
        )
        self.assertEqual(
            normalize_http_url("https://example.com:8443/").origin,
            "https://example.com:8443",
        )

    def test_removes_all_supported_tracking_parameters_case_insensitively(self) -> None:
        raw = (
            "https://example.com/?keep=yes&utm_source=a&UTM_MEDIUM=b&"
            "utm_campaign=c&utm_term=d&utm_content=e&fbclid=f&gclid=g&msclkid=m"
        )
        self.assertEqual(
            normalize_http_url(raw).url,
            "https://example.com/?keep=yes",
        )

    def test_rejects_invalid_or_unsafe_url_syntax(self) -> None:
        cases = (
            "",
            "   ",
            "ftp://example.com/",
            "https:///missing-host",
            "https://user@example.com/",
            "https://user:secret@example.com/",
            "https://example.com:99999/",
            "https://example.com:%38%30/",
            "https://example.com/\r\nInjected: value",
            "https://example.com/\x00bad",
            "https://[fe80::1%25eth0]/",
        )
        for raw in cases:
            with self.subTest(raw=repr(raw)):
                with self.assertRaises(InvalidUrl):
                    normalize_http_url(raw)

    def test_enforces_url_and_hostname_limits(self) -> None:
        with self.assertRaises(InvalidUrl):
            normalize_http_url("https://example.com/" + ("x" * 4090))
        with self.assertRaises(InvalidUrl):
            normalize_http_url("https://" + ("a" * 64) + ".example/")

    def test_same_origin_does_not_merge_scheme_port_or_www(self) -> None:
        root = normalize_http_url("https://example.com/")
        self.assertTrue(same_origin(root, normalize_http_url("https://example.com/a")))
        self.assertFalse(same_origin(root, normalize_http_url("http://example.com/")))
        self.assertFalse(same_origin(root, normalize_http_url("https://www.example.com/")))
        self.assertFalse(same_origin(root, normalize_http_url("https://example.com:8443/")))


if __name__ == "__main__":
    unittest.main()
