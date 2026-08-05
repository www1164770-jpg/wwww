from __future__ import annotations

import unittest

from backend.crawler.net.policy import DnsFailure, NetworkPolicy, UnsafeTarget
from backend.crawler.net.url import normalize_http_url


class SequenceResolver:
    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = 0

    def __call__(self, hostname: str, port: int):
        answer = self.answers[min(self.calls, len(self.answers) - 1)]
        self.calls += 1
        if isinstance(answer, BaseException):
            raise answer
        return answer


class NetworkPolicyTests(unittest.TestCase):
    def test_accepts_only_all_public_addresses(self) -> None:
        resolver = SequenceResolver(
            [["93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946"]]
        )
        target = NetworkPolicy(resolver=resolver).check_url(
            normalize_http_url("https://example.com/")
        )

        self.assertEqual(len(target.addresses), 2)
        self.assertEqual(target.hostname, "example.com")

    def test_rejects_local_metadata_private_and_special_addresses(self) -> None:
        cases = (
            ("http://localhost/", ["93.184.216.34"]),
            ("http://sub.localhost/", ["93.184.216.34"]),
            ("http://metadata.google.internal/", ["93.184.216.34"]),
            ("http://127.0.0.1/", ["127.0.0.1"]),
            ("http://10.0.0.1/", ["10.0.0.1"]),
            ("http://169.254.169.254/", ["169.254.169.254"]),
            ("http://224.0.0.1/", ["224.0.0.1"]),
            ("http://192.0.2.1/", ["192.0.2.1"]),
            ("http://198.18.0.1/", ["198.18.0.1"]),
            ("http://[::1]/", ["::1"]),
            ("http://[fe80::1]/", ["fe80::1"]),
            ("http://[2001:db8::1]/", ["2001:db8::1"]),
            ("http://[::ffff:10.0.0.1]/", ["::ffff:10.0.0.1"]),
        )
        for url, addresses in cases:
            with self.subTest(url=url):
                with self.assertRaises(UnsafeTarget):
                    NetworkPolicy(
                        resolver=SequenceResolver([addresses])
                    ).check_url(normalize_http_url(url))

    def test_one_private_answer_rejects_entire_dns_result(self) -> None:
        with self.assertRaises(UnsafeTarget):
            NetworkPolicy(
                resolver=SequenceResolver(
                    [["93.184.216.34", "10.0.0.5"]]
                )
            ).check_url(normalize_http_url("https://example.com/"))

    def test_empty_or_failed_dns_is_classified(self) -> None:
        for answer in ([], OSError("resolver unavailable")):
            with self.subTest(answer=repr(answer)):
                with self.assertRaises(DnsFailure):
                    NetworkPolicy(
                        resolver=SequenceResolver([answer])
                    ).check_url(normalize_http_url("https://example.com/"))

    def test_short_cache_and_force_refresh_prevent_dns_rebinding(self) -> None:
        clock = [100.0]
        resolver = SequenceResolver(
            [["93.184.216.34"], ["10.0.0.7"], ["93.184.216.34"]]
        )
        policy = NetworkPolicy(
            resolver=resolver,
            cache_ttl_seconds=10,
            monotonic=lambda: clock[0],
        )
        url = normalize_http_url("https://example.com/")

        policy.check_url(url)
        policy.check_url(url)
        self.assertEqual(resolver.calls, 1)
        with self.assertRaises(UnsafeTarget):
            policy.check_url(url, force_refresh=True)
        self.assertEqual(resolver.calls, 2)

        clock[0] = 111.0
        policy.check_url(url)
        self.assertEqual(resolver.calls, 3)


if __name__ == "__main__":
    unittest.main()
