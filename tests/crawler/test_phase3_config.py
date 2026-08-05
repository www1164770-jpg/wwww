from __future__ import annotations

import unittest

from backend.crawler.config import CrawlerConfigError, CrawlerSettings


class PhaseThreeConfigTests(unittest.TestCase):
    def test_phase_three_defaults_are_safe_and_disabled(self) -> None:
        settings = CrawlerSettings.from_env({})
        self.assertFalse(settings.analysis_enabled)
        self.assertFalse(settings.icon_fetch_enabled)
        self.assertEqual(settings.analysis_rule_version, "analysis-rules-v1")
        self.assertEqual(settings.risk_rule_version, "risk-rules-v1")
        self.assertTrue(settings.ollama_endpoint.startswith("http://127.0.0.1:"))
        self.assertLessEqual(settings.icon_max_bytes, 10_485_760)
        self.assertLessEqual(settings.icon_max_pixels, 67_108_864)

    def test_phase_three_values_are_parsed(self) -> None:
        settings = CrawlerSettings.from_env(
            {
                "CRAWLER_ANALYSIS_ENABLED": "true",
                "CRAWLER_ICON_FETCH_ENABLED": "yes",
                "CRAWLER_ANALYSIS_CONFIDENCE_THRESHOLD": "0.9",
                "CRAWLER_OLLAMA_TIMEOUT_SECONDS": "4.5",
                "CRAWLER_ICON_MAX_BYTES": "2048",
                "CRAWLER_ICON_MAX_PIXELS": "4096",
                "CRAWLER_ICON_MAX_REDIRECTS": "2",
            }
        )
        self.assertTrue(settings.analysis_enabled)
        self.assertTrue(settings.icon_fetch_enabled)
        self.assertEqual(settings.analysis_confidence_threshold, 0.9)
        self.assertEqual(settings.ollama_timeout_seconds, 4.5)
        self.assertEqual(settings.icon_max_bytes, 2048)
        self.assertEqual(settings.icon_max_pixels, 4096)
        self.assertEqual(settings.icon_max_redirects, 2)

    def test_invalid_phase_three_limits_and_boolean_are_rejected(self) -> None:
        for environment in (
            {"CRAWLER_ANALYSIS_ENABLED": "sometimes"},
            {"CRAWLER_ICON_FETCH_ENABLED": "perhaps"},
            {"CRAWLER_ANALYSIS_CONFIDENCE_THRESHOLD": "0.1"},
            {"CRAWLER_OLLAMA_TIMEOUT_SECONDS": "0"},
            {"CRAWLER_ICON_MAX_BYTES": "12"},
            {"CRAWLER_ICON_MAX_PIXELS": "12"},
        ):
            with self.subTest(environment=environment):
                with self.assertRaises(CrawlerConfigError):
                    CrawlerSettings.from_env(environment)


if __name__ == "__main__":
    unittest.main()
