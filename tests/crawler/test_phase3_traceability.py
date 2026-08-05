from __future__ import annotations

import io
import json
import unittest

from backend.crawler.analysis.contract import AnalysisSpec, analysis_key, canonical_json, input_snapshot, sanitize_provider_response
from backend.crawler.cli import main
from backend.crawler.db.migration import MIGRATION_DIR, _migration_statements
from backend.crawler.review.targets import DisabledPublishTarget, InMemoryPublishTarget, PublishCommand
from backend.crawler.review.mapping import WebsiteFields
from backend.crawler.review.publish import PublishUnavailable


class AnalysisTraceabilityTests(unittest.TestCase):
    def test_keys_are_stable_and_version_or_content_changes_create_new_identity(self):
        base = AnalysisSpec(model_version="m1", prompt_version="p1", taxonomy_version="t1", scoring_version="s1")
        key = analysis_key(fetch_result_uid="fetch-a", content_hash="a" * 64, spec=base)
        self.assertEqual(key, analysis_key(fetch_result_uid="fetch-a", content_hash="a" * 64, spec=base))
        self.assertNotEqual(key, analysis_key(fetch_result_uid="fetch-a", content_hash="b" * 64, spec=base))
        self.assertNotEqual(key, analysis_key(fetch_result_uid="fetch-a", content_hash="a" * 64, spec=AnalysisSpec(model_version="m2", prompt_version="p1", taxonomy_version="t1", scoring_version="s1")))

    def test_snapshot_and_provider_response_are_bounded_canonical_and_redacted(self):
        snapshot = input_snapshot(title="标题😀\x00", meta_description="x" * 3000, heading=None, text_excerpt="body", normalized_url="https://example.test/?token=secret", language="zh-CN", content_type="text/html", content_hash="a" * 64)
        self.assertLessEqual(len(snapshot["meta_description"] or ""), 2000)
        self.assertNotIn("secret", snapshot["normalized_url"] or "")
        self.assertEqual(canonical_json({"b": 1, "a": "😀"}), canonical_json({"a": "😀", "b": 1}))
        sanitized = sanitize_provider_response({"api_key": "key", "url": "https://x.test/?password=p", "deep": {"a": {"b": {"c": {"d": {"e": "hidden"}}}}}})
        self.assertEqual(sanitized["api_key"], "[REDACTED]")
        self.assertNotIn("password=p", sanitized["url"])
        self.assertIn("[TRUNCATED_DEPTH]", json.dumps(sanitized))

    def test_traceability_migration_is_forward_only(self):
        statements = _migration_statements(MIGRATION_DIR / "0006_analysis_traceability.sql")
        text = "\n".join(statements).upper()
        self.assertIn("ANALYSIS_KEY", text)
        self.assertIn("SOURCE_INPUT_SNAPSHOT_HASH", text)
        for forbidden in ("DROP ", "TRUNCATE", "DELETE", "CREATE DATABASE", "NAV_SITE"):
            self.assertNotIn(forbidden, text)


class PublishTargetContractTests(unittest.TestCase):
    def test_disabled_target_never_creates_records(self):
        target = DisabledPublishTarget()
        fields = WebsiteFields("name", "https://example.test/", None, None, None, 1, None)
        with self.assertRaises(PublishUnavailable):
            target.publish(PublishCommand("key", fields))

    def test_in_memory_target_is_idempotent_and_recovers_lost_response(self):
        target = InMemoryPublishTarget(lose_response_after_write=True)
        fields = WebsiteFields("name", "https://example.test/", None, None, None, 1, None)
        command = PublishCommand("key", fields)
        with self.assertRaises(TimeoutError):
            target.publish(command)
        recovered = target.find_by_idempotency_key("key")
        self.assertIsNotNone(recovered)
        self.assertEqual(target.publish(command), recovered)
        self.assertEqual(len(target.records), 1)
        self.assertEqual(target.calls, 2)


class ReadinessTests(unittest.TestCase):
    def test_readiness_never_requires_or_emits_database_urls(self):
        output, errors = io.StringIO(), io.StringIO()
        code = main(["integration-readiness", "--json"], environ={}, stdout=output, stderr=errors)
        self.assertEqual(code, 2)
        payload = json.loads(output.getvalue())
        self.assertFalse(payload["data"]["crawler_database_configured"])
        self.assertNotIn("mysql://", output.getvalue().lower())
