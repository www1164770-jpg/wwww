from __future__ import annotations

from datetime import datetime
import unittest

from sqlalchemy import select

from backend.crawler.db import AnalysisResult, FetchResult, PublishPreview as StoredPublishPreview, PublishRecord, ReviewEvent
from backend.crawler.review.mapping import MappingValidationError, build_website_fields
from backend.crawler.review.preview import create_local_preview, detect_duplicates
from backend.crawler.review.publish import execute_publish, publish_preview
from backend.crawler.review.targets import InMemoryPublishTarget
from backend.crawler.review.service import (
    ReviewVersionConflict, approve_review, assign_review, create_review,
    mark_publish_ready, reject_review, update_review,
)
from backend.crawler.review.states import APPROVED, PENDING, PUBLISHED, REJECTED, REVIEWING
from tests.crawler.support import NOW, sqlite_session


def source(session):
    fetch = FetchResult(
        result_uid="fetch-phase4", requested_url="https://example.com/?utm_source=test",
        normalized_url="https://example.com/", normalized_fingerprint="a" * 64,
        status="success", title="Example", content_hash="b" * 64, fetched_at=NOW,
    )
    session.add(fetch)
    session.flush()
    analysis = AnalysisResult(
        analysis_uid="analysis-phase4", fetch_result_id=fetch.id, candidate_uid="site-a",
        analysis_version="v1", content_hash="b" * 64, detected_language="zh",
        language_confidence=0.9, category="tools", category_confidence=0.9,
        quality_score=0.9, title_original="示例网站", summary_zh="中文摘要",
        summary_method="rules", tags_json=[], rule_version="v1", model_status="not_used",
        evidence_hashes_json=[],
    )
    session.add(analysis)
    session.flush()
    return fetch, analysis


def case(session):
    fetch, analysis = source(session)
    return create_review(session, fetch_result_id=fetch.id, analysis_result_id=analysis.id)


class FakePublisher:
    def __init__(self, sites=()):
        self.sites = list(sites)
        self.created = []

    def list_sites(self):
        return list(self.sites)

    def create_website(self, fields):
        record = {"id": len(self.sites) + 1, "name": fields.name, "url": fields.url}
        self.sites.append(record)
        self.created.append(record)
        return record


class PhaseFourReviewTests(unittest.TestCase):
    def test_create_copies_ai_suggestions_but_remains_pending(self):
        with sqlite_session() as session:
            review = case(session)
            self.assertEqual(review.status, PENDING)
            self.assertEqual(review.selected_title, "示例网站")
            self.assertEqual(session.scalar(select(ReviewEvent)).event_type, "review_created")

    def test_state_machine_and_event_audit(self):
        with sqlite_session() as session:
            review = case(session)
            review = assign_review(session, review, reviewer_id="admin-a", expected_version=1, actor_id="admin-a")
            self.assertEqual(review.status, REVIEWING)
            review = approve_review(session, review, expected_version=2, actor_id="admin-a")
            self.assertEqual(review.status, APPROVED)
            events = list(session.scalars(select(ReviewEvent).order_by(ReviewEvent.created_at)).all())
            self.assertEqual([event.next_status for event in events], [PENDING, REVIEWING, APPROVED])

    def test_pending_or_reviewing_can_be_rejected_but_not_reopened(self):
        with sqlite_session() as session:
            review = reject_review(session, case(session), expected_version=1, actor_id="admin")
            self.assertEqual(review.status, REJECTED)
            with self.assertRaises(ValueError):
                assign_review(session, review, reviewer_id="admin", expected_version=2, actor_id="admin")

    def test_stale_version_is_rejected(self):
        with sqlite_session() as session:
            review = case(session)
            assign_review(session, review, reviewer_id="admin", expected_version=1, actor_id="admin")
            with self.assertRaises(ReviewVersionConflict):
                update_review(session, review, expected_version=1, changes={"selected_title": "new"}, actor_id="admin")

    def test_edit_is_audited_and_accepts_unicode(self):
        with sqlite_session() as session:
            review = case(session)
            edited = update_review(session, review, expected_version=1, changes={"selected_title": "工具导航 🧭"}, actor_id="admin")
            self.assertEqual(edited.selected_title, "工具导航 🧭")
            event = session.scalar(select(ReviewEvent).where(ReviewEvent.event_type == "review_updated"))
            self.assertEqual(event.metadata_json["changed_fields"], ["selected_title"])

    def test_mapping_normalizes_url_and_checks_known_model_lengths(self):
        with sqlite_session() as session:
            review = case(session)
            fields = build_website_fields(review, category_resolver=lambda category: 7 if category == "tools" else None)
            self.assertEqual(fields.name, "示例网站")
            self.assertEqual(fields.url, "https://example.com/")
            self.assertEqual(fields.category_id, 7)
            review.selected_title = "x" * 101
            with self.assertRaises(MappingValidationError):
                build_website_fields(review, category_resolver=lambda _: 7)


class PhaseFourPreviewAndPublishTests(unittest.TestCase):
    def test_preview_classifies_all_duplicate_forms_without_writes(self):
        self.assertEqual(detect_duplicates("https://example.com/", []).result, "no_match")
        self.assertEqual(detect_duplicates("https://example.com/", [{"id": 1, "url": "https://example.com/"}]).result, "exact_match")
        self.assertEqual(detect_duplicates("https://example.com/?utm_source=x", [{"id": 1, "url": "https://example.com/"}]).result, "canonical_match")
        self.assertEqual(detect_duplicates("https://example.com/path", [{"id": 1, "url": "https://example.com/other"}]).result, "domain_match")
        self.assertEqual(detect_duplicates("https://example.com/", [{"id": 1, "url": "https://example.com/"}, {"id": 2, "url": "https://example.com/?utm_source=x"}]).result, "conflict")

    def test_preview_is_read_only_and_publish_requires_confirmation(self):
        with sqlite_session() as session:
            review = case(session)
            fields = build_website_fields(review, category_resolver=lambda _: 1)
            publisher = FakePublisher()
            self.assertEqual(publish_preview(fields, publisher).result, "no_match")
            self.assertEqual(publisher.created, [])
            with self.assertRaises(PermissionError):
                execute_publish(session, case=review, fields=fields, publisher=publisher, confirmed=False, actor_id="admin", expected_version=1)

    def test_local_preview_is_persisted_and_never_queries_a_target(self):
        with sqlite_session() as session:
            review = case(session)
            review = assign_review(session, review, reviewer_id="admin", expected_version=1, actor_id="admin")
            review = approve_review(session, review, expected_version=2, actor_id="admin")
            review, preview = create_local_preview(session, review, expected_version=3, actor_id="admin")
            self.assertEqual(review.status, "publish_ready")
            self.assertEqual(preview.review_version, review.version)
            self.assertEqual(preview.result_json["result"], "local_validation_only")
            self.assertEqual(session.scalar(select(StoredPublishPreview)).preview_uid, preview.preview_uid)

    def test_publish_is_idempotent_and_transitions_only_after_explicit_ready(self):
        with sqlite_session() as session:
            review = case(session)
            review = assign_review(session, review, reviewer_id="admin", expected_version=1, actor_id="admin")
            review = approve_review(session, review, expected_version=2, actor_id="admin")
            review, preview = create_local_preview(session, review, expected_version=3, actor_id="admin")
            fields = build_website_fields(review, category_resolver=lambda _: 1)
            publisher = FakePublisher()
            first = execute_publish(session, case=review, fields=fields, publisher=publisher, confirmed=True, actor_id="admin", expected_version=4, stored_preview=preview)
            second = execute_publish(session, case=review, fields=fields, publisher=publisher, confirmed=True, actor_id="admin", expected_version=5, stored_preview=preview)
            self.assertTrue(first.published)
            self.assertTrue(second.published)
            self.assertEqual(review.status, PUBLISHED)
            self.assertEqual(len(publisher.created), 1)
            self.assertEqual(len(list(session.scalars(select(PublishRecord)))), 1)

    def test_target_response_loss_recovers_without_a_second_target_write(self):
        with sqlite_session() as session:
            review = case(session)
            review = assign_review(session, review, reviewer_id="admin", expected_version=1, actor_id="admin")
            review = approve_review(session, review, expected_version=2, actor_id="admin")
            review, preview = create_local_preview(session, review, expected_version=3, actor_id="admin")
            fields = build_website_fields(review, category_resolver=lambda _: 1)
            target = InMemoryPublishTarget(lose_response_after_write=True)
            failed = execute_publish(session, case=review, fields=fields, publisher=target, confirmed=True, actor_id="admin", expected_version=4, stored_preview=preview)
            self.assertFalse(failed.published)
            self.assertEqual(review.status, "publish_failed")
            recovered = execute_publish(session, case=review, fields=fields, publisher=target, confirmed=True, actor_id="admin", expected_version=6, stored_preview=preview)
            self.assertTrue(recovered.published)
            self.assertEqual(len(target.records), 1)
            self.assertEqual(target.calls, 1)
