from __future__ import annotations

import unittest

from backend.crawler.analysis import (
    AnalysisDocument,
    ModelFailure,
    analyze_document,
    detect_language,
)


def document(**overrides) -> AnalysisDocument:
    values = {
        "source_uid": "fetch-1",
        "candidate_uid": "site-1",
        "content_hash": "a" * 64,
        "title": "开放课程与学习资源",
        "description": "提供大学课程、学习资料和教学工具。",
        "heading": "免费教育资源",
        "text_excerpt": "这里汇集课程、学习资料、教师工具和大学公开课。",
        "declared_language": "zh-CN",
    }
    values.update(overrides)
    return AnalysisDocument(**values)


class FakeModel:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def analyze(self, payload):
        self.calls.append(payload)
        if self.error is not None:
            raise self.error
        return self.result


class PhaseThreeAnalysisTests(unittest.TestCase):
    def test_high_confidence_rules_do_not_call_model(self) -> None:
        model = FakeModel(error=AssertionError("model must not be called"))

        result = analyze_document(document(), model=model)

        self.assertEqual(model.calls, [])
        self.assertEqual(result.category, "education")
        self.assertGreaterEqual(result.category_confidence, 0.85)
        self.assertEqual(result.detected_language, "zh")
        self.assertEqual(result.model_status, "not_needed")
        self.assertEqual(result.summary_method, "rules")
        self.assertLessEqual(len(result.summary_zh), 160)
        self.assertIn("开放课程", result.summary_zh)

    def test_low_confidence_result_uses_schema_checked_model(self) -> None:
        model = FakeModel(
            {
                "category": "productivity",
                "confidence": 0.91,
                "summary_zh": "该网站提供团队任务管理和协作看板。",
                "tags_zh": ["任务管理", "团队协作"],
                "evidence": ["team task management", "collaboration boards"],
            }
        )
        source = document(
            title="Acme Workspace",
            description="Team task management and collaboration boards.",
            heading="Plan work together",
            text_excerpt="Team task management and collaboration boards for small groups.",
            declared_language="en",
        )

        result = analyze_document(source, model=model)

        self.assertEqual(len(model.calls), 1)
        self.assertEqual(result.category, "productivity")
        self.assertEqual(result.model_status, "used")
        self.assertEqual(result.summary_method, "model")
        self.assertEqual(result.tags_zh, ("任务管理", "团队协作"))
        self.assertTrue(result.evidence_hashes)
        self.assertNotIn("text_excerpt", model.calls[0])
        self.assertLessEqual(len(model.calls[0]["evidence_text"]), 2400)

    def test_timeout_invalid_json_and_resource_exhaustion_keep_rule_fallback(self) -> None:
        cases = (
            ModelFailure("timeout"),
            ModelFailure("invalid_json"),
            ModelFailure("resource_exhausted"),
        )
        source = document(
            title="Acme",
            description=None,
            heading=None,
            text_excerpt="A small public website.",
            declared_language="en",
        )
        for error in cases:
            with self.subTest(code=error.code):
                model = FakeModel(error=error)
                result = analyze_document(source, model=model)
                self.assertEqual(result.model_status, "model_unavailable")
                self.assertEqual(result.model_error_code, error.code)
                self.assertEqual(result.summary_method, "rules_fallback")
                self.assertTrue(result.summary_zh)

        unsupported = FakeModel(
            {
                "category": "education",
                "confidence": 0.99,
                "summary_zh": "虚构事实。",
                "tags_zh": ["教育"],
                "evidence": ["not present in source"],
            }
        )
        result = analyze_document(source, model=unsupported)
        self.assertEqual(result.model_status, "model_unavailable")
        self.assertEqual(result.model_error_code, "invalid_schema")

    def test_multilingual_detection_is_deterministic(self) -> None:
        cases = (
            ("这是一个中文学习网站，提供丰富课程。", "zh"),
            ("This is an English reference website with detailed guides.", "en"),
            ("これは日本語の学習サイトです。", "ja"),
            ("Это русскоязычный справочный сайт.", "ru"),
        )
        for text, expected in cases:
            with self.subTest(expected=expected):
                language, confidence = detect_language(text)
                self.assertEqual(language, expected)
                self.assertGreaterEqual(confidence, 0.6)


if __name__ == "__main__":
    unittest.main()
