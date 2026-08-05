from __future__ import annotations

import unittest

from backend.crawler.analysis import AnalysisDocument, analyze_document
from backend.crawler.risk import assess_risk


def analyzed(text: str, *, confidence: float | None = None):
    document = AnalysisDocument(
        source_uid="fetch-risk",
        candidate_uid="site-risk",
        content_hash="b" * 64,
        title="Public resource",
        description=text,
        heading=None,
        text_excerpt=text,
        declared_language="en",
    )
    result = analyze_document(document)
    if confidence is not None:
        result = result.with_confidence(confidence)
    return document, result


class PhaseThreeRiskTests(unittest.TestCase):
    def test_forbidden_categories_are_hard_rejected_with_minimal_evidence(self) -> None:
        cases = (
            ("adult explicit pornography portal", "hard_adult"),
            ("online casino gambling and betting", "hard_gambling"),
            ("buy illegal narcotics and cocaine", "hard_drugs"),
            ("firearms weapons marketplace", "hard_weapons"),
            ("credential phishing login verification", "hard_phishing"),
            ("malware ransomware payload download", "hard_malware"),
            ("pirated cracked software downloads", "hard_piracy"),
            ("violent extremist propaganda", "hard_extremism"),
        )
        for text, rule_code in cases:
            with self.subTest(rule_code=rule_code):
                source, analysis = analyzed(text)
                decision = assess_risk(source, analysis)
                self.assertEqual(decision.status, "rejected")
                self.assertTrue(decision.hard_reject)
                self.assertIn(rule_code, decision.rule_codes)
                self.assertTrue(all(len(item) == 64 for item in decision.evidence_hashes))
                self.assertNotIn(text, repr(decision))

    def test_model_category_cannot_override_hard_reject(self) -> None:
        source, analysis = analyzed("online casino gambling and betting")
        analysis = analysis.with_model_category("education", 0.99)

        decision = assess_risk(source, analysis)

        self.assertEqual(decision.status, "rejected")
        self.assertTrue(decision.hard_reject)

    def test_low_confidence_requires_review_and_high_quality_can_approve(self) -> None:
        low_source, low = analyzed("A public website.", confidence=0.4)
        low_decision = assess_risk(low_source, low)
        self.assertEqual(low_decision.status, "review_required")
        self.assertFalse(low_decision.hard_reject)

        good_source, good = analyzed(
            "Open university courses, detailed learning guides, teacher tools, and free study materials."
        )
        good_decision = assess_risk(good_source, good)
        self.assertEqual(good_decision.status, "approved")
        self.assertFalse(good_decision.hard_reject)


if __name__ == "__main__":
    unittest.main()
