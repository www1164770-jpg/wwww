"""Crawler-owned human review service with audit events and optimistic locks."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.crawler.db import AnalysisResult, FetchResult, IconAsset, RiskDecision
from backend.crawler.db.base import utc_now
from backend.crawler.db.models import PublishPreview, ReviewCase, ReviewEvent
from backend.crawler.review.states import APPROVED, PENDING, PUBLISH_FAILED, PUBLISH_READY, PUBLISHED, PUBLISHING, REJECTED, REVIEWING, assert_review_transition

EDITABLE_FIELDS = frozenset({"priority", "selected_title", "selected_summary", "selected_description", "selected_category", "selected_region", "selected_language", "selected_tags", "selected_risk_level", "selected_quality_score", "selected_url", "selected_logo_asset_id", "risk_acknowledgements", "override_reasons"})


class ReviewVersionConflict(RuntimeError):
    """A user attempted to save an obsolete version."""


class ReviewValidationError(ValueError):
    """Review inputs violate the crawler-owned data contract."""


def _clean_note(value: str | None, maximum: int = 4000) -> str | None:
    if value is None:
        return None
    return "".join(char for char in str(value) if ord(char) >= 32 or char in "\n\t").strip()[:maximum] or None


def review_content_hash(case: ReviewCase, changes: dict[str, Any] | None = None) -> str:
    """Stable hash of human-editable publish content, not AI raw output."""
    values = {name: (changes[name] if changes and name in changes else getattr(case, name)) for name in EDITABLE_FIELDS}
    return sha256(json.dumps(values, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()


def _event(session: Session, case: ReviewCase, *, actor_id: str, actor_type: str, event_type: str, previous_status: str | None = None, next_status: str | None = None, reason_code: str | None = None, notes: str | None = None, metadata: dict[str, Any] | None = None) -> None:
    session.add(ReviewEvent(event_uid=uuid4().hex, review_case_id=case.id, actor_type=str(actor_type)[:32], actor_id=str(actor_id)[:128], event_type=event_type[:64], previous_status=previous_status, next_status=next_status, reason_code=reason_code[:64] if reason_code else None, notes_sanitized=_clean_note(notes), metadata_json=metadata or None, review_version=case.version, changed_fields_json=(metadata or {}).get("changed_fields"), created_at=utc_now()))


def _sources(session: Session, fetch_result_id: int, analysis_result_id: int) -> tuple[FetchResult, AnalysisResult]:
    fetched, analysis = session.get(FetchResult, fetch_result_id), session.get(AnalysisResult, analysis_result_id)
    if fetched is None or analysis is None or analysis.fetch_result_id != fetched.id:
        raise ReviewValidationError("review must use matching fetch and analysis results")
    if not fetched.content_hash or fetched.content_hash != analysis.content_hash:
        raise ReviewValidationError("review source content hash does not match analysis")
    return fetched, analysis


def _validate_logo(session: Session, asset_id: int | None, fetch_result_id: int) -> None:
    if asset_id is not None:
        asset = session.get(IconAsset, asset_id)
        if asset is None or asset.fetch_result_id != fetch_result_id:
            raise ReviewValidationError("logo must be a verified Phase 3 asset for this fetch")


def create_review(session: Session, *, fetch_result_id: int, analysis_result_id: int, actor_id: str = "system", actor_type: str = "system", priority: int = 100, selected_logo_asset_id: int | None = None) -> ReviewCase:
    """Create a review; copied analysis fields are suggestions, never a decision."""
    fetched, analysis = _sources(session, fetch_result_id, analysis_result_id)
    _validate_logo(session, selected_logo_asset_id, fetched.id)
    existing = session.scalar(select(ReviewCase).where(ReviewCase.analysis_result_id == analysis.id, ReviewCase.source_content_hash == analysis.content_hash))
    if existing is not None:
        return existing
    case = ReviewCase(review_uid=uuid4().hex, fetch_result_id=fetched.id, analysis_result_id=analysis.id, source_content_hash=analysis.content_hash, source_analysis_uid=analysis.analysis_uid, source_analysis_version=analysis.analysis_version, source_input_snapshot_hash=analysis.input_snapshot_hash, source_analyzer_type=analysis.analyzer_type, source_model_version=analysis.model_version, source_prompt_version=analysis.prompt_version, source_taxonomy_version=analysis.taxonomy_version, source_scoring_version=analysis.scoring_version, status=PENDING, priority=int(priority), selected_title=analysis.title_original or fetched.title, selected_summary=analysis.summary_zh, selected_description=fetched.meta_description or fetched.text_excerpt, selected_category=analysis.category, selected_language=analysis.detected_language, selected_tags=list(analysis.tags_json), selected_quality_score=analysis.quality_score, selected_url=fetched.final_url or fetched.normalized_final_url or fetched.normalized_url, selected_logo_asset_id=selected_logo_asset_id, version=1)
    case.review_content_hash = review_content_hash(case)
    session.add(case)
    session.flush()
    _event(session, case, actor_id=actor_id, actor_type=actor_type, event_type="review_created", next_status=PENDING)
    session.flush()
    return case


def _change(session: Session, case: ReviewCase, *, expected_version: int, values: dict[str, Any], actor_id: str, actor_type: str, event_type: str, previous_status: str | None = None, next_status: str | None = None, reason_code: str | None = None, notes: str | None = None, metadata: dict[str, Any] | None = None) -> ReviewCase:
    if case.version != expected_version:
        raise ReviewVersionConflict("review case was changed by another reviewer")
    changed_content = bool(set(values).intersection(EDITABLE_FIELDS))
    if changed_content:
        values["review_content_hash"] = review_content_hash(case, values)
        session.query(PublishPreview).filter(
            PublishPreview.review_case_id == case.id,
            PublishPreview.invalidated_at.is_(None),
        ).update({"invalidated_at": utc_now(), "invalidated_reason": "review_changed"}, synchronize_session=False)
    values = {**values, "version": expected_version + 1, "updated_at": utc_now()}
    result = session.execute(update(ReviewCase).where(ReviewCase.id == case.id, ReviewCase.version == expected_version).values(**values))
    if result.rowcount != 1:
        raise ReviewVersionConflict("review case was changed by another reviewer")
    for key, value in values.items():
        setattr(case, key, value)
    _event(session, case, actor_id=actor_id, actor_type=actor_type, event_type=event_type, previous_status=previous_status, next_status=next_status, reason_code=reason_code, notes=notes, metadata=metadata)
    session.flush()
    return case


def assign_review(session: Session, case: ReviewCase, *, reviewer_id: str, expected_version: int, actor_id: str, actor_type: str = "admin") -> ReviewCase:
    assert_review_transition(case.status, REVIEWING)
    reviewer = str(reviewer_id).strip()
    if not reviewer:
        raise ReviewValidationError("reviewer id is required")
    return _change(session, case, expected_version=expected_version, values={"status": REVIEWING, "assigned_reviewer_id": reviewer[:128], "assigned_at": utc_now()}, actor_id=actor_id, actor_type=actor_type, event_type="review_assigned", previous_status=PENDING, next_status=REVIEWING, metadata={"reviewer_id": reviewer[:128]})


def update_review(session: Session, case: ReviewCase, *, expected_version: int, changes: dict[str, Any], actor_id: str, actor_type: str = "admin", notes: str | None = None) -> ReviewCase:
    if case.status not in {PENDING, REVIEWING}:
        raise ReviewValidationError("only pending or reviewing cases may be edited")
    if not changes or not set(changes).issubset(EDITABLE_FIELDS):
        raise ReviewValidationError("review includes unsupported editable fields")
    if "selected_logo_asset_id" in changes:
        _validate_logo(session, changes["selected_logo_asset_id"], case.fetch_result_id)
    return _change(session, case, expected_version=expected_version, values=dict(changes), actor_id=actor_id, actor_type=actor_type, event_type="review_updated", previous_status=case.status, next_status=case.status, notes=notes, metadata={"changed_fields": sorted(changes)})


def _assert_risk_override(session: Session, case: ReviewCase, can_override_risk: bool) -> None:
    decision = session.scalar(select(RiskDecision).where(RiskDecision.analysis_result_id == case.analysis_result_id).order_by(RiskDecision.created_at.desc()))
    has_reason = isinstance(case.override_reasons, (dict, list)) and bool(case.override_reasons)
    if decision is not None and decision.hard_reject and (not can_override_risk or not has_reason):
        raise PermissionError("hard risk requires authorized override with a reason")


def approve_review(session: Session, case: ReviewCase, *, expected_version: int, actor_id: str, actor_type: str = "admin", reason_code: str | None = None, notes: str | None = None, can_override_risk: bool = False) -> ReviewCase:
    assert_review_transition(case.status, APPROVED)
    _assert_risk_override(session, case, can_override_risk)
    now = utc_now()
    return _change(session, case, expected_version=expected_version, values={"status": APPROVED, "decision_at": now, "approved_at": now}, actor_id=actor_id, actor_type=actor_type, event_type="review_approved", previous_status=case.status, next_status=APPROVED, reason_code=reason_code, notes=notes)


def reject_review(session: Session, case: ReviewCase, *, expected_version: int, actor_id: str, actor_type: str = "admin", reason_code: str | None = None, notes: str | None = None) -> ReviewCase:
    assert_review_transition(case.status, REJECTED)
    now = utc_now()
    return _change(session, case, expected_version=expected_version, values={"status": REJECTED, "decision_at": now, "rejected_at": now}, actor_id=actor_id, actor_type=actor_type, event_type="review_rejected", previous_status=case.status, next_status=REJECTED, reason_code=reason_code, notes=notes)


def request_changes(session: Session, case: ReviewCase, **kwargs: Any) -> ReviewCase:
    return reject_review(session, case, **kwargs)


def mark_publish_ready(session: Session, case: ReviewCase, *, expected_version: int, actor_id: str, actor_type: str = "admin") -> ReviewCase:
    assert_review_transition(case.status, PUBLISH_READY)
    return _change(session, case, expected_version=expected_version, values={"status": PUBLISH_READY, "publish_ready_at": utc_now()}, actor_id=actor_id, actor_type=actor_type, event_type="publish_preview_ready", previous_status=APPROVED, next_status=PUBLISH_READY)


def mark_published(session: Session, case: ReviewCase, *, expected_version: int, actor_id: str = "system", actor_type: str = "system") -> ReviewCase:
    assert_review_transition(case.status, PUBLISHED)
    return _change(session, case, expected_version=expected_version, values={"status": PUBLISHED, "published_at": utc_now()}, actor_id=actor_id, actor_type=actor_type, event_type="publish_succeeded", previous_status=PUBLISHING, next_status=PUBLISHED)


def mark_publishing(session: Session, case: ReviewCase, *, expected_version: int, actor_id: str, actor_type: str = "admin") -> ReviewCase:
    assert_review_transition(case.status, PUBLISHING)
    return _change(session, case, expected_version=expected_version, values={"status": PUBLISHING}, actor_id=actor_id, actor_type=actor_type, event_type="publish_started", previous_status=case.status, next_status=PUBLISHING)


def mark_publish_failed(session: Session, case: ReviewCase, *, expected_version: int, actor_id: str, actor_type: str = "system", reason_code: str = "sync_failed") -> ReviewCase:
    assert_review_transition(case.status, PUBLISH_FAILED)
    return _change(session, case, expected_version=expected_version, values={"status": PUBLISH_FAILED}, actor_id=actor_id, actor_type=actor_type, event_type="publish_failed", previous_status=PUBLISHING, next_status=PUBLISH_FAILED, reason_code=reason_code)


create_review_case = create_review
assign_reviewer = assign_review
submit_review = update_review
