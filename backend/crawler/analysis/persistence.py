"""Idempotent Phase 3 analysis task and result persistence."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.crawler.db import AnalysisResult, FetchResult, RiskDecision, utc_now
from backend.crawler.queue.tasks import EnqueueResult, enqueue_task
from backend.crawler.risk import RiskAssessment

from .contract import AnalysisSpec, analysis_key, canonical_json, input_snapshot
from .service import AnalysisDocument, AnalysisOutcome


ANALYSIS_TASK_SCHEMA = "phase3-analysis-task-v2"
CONTENT_ANALYSIS_TASK_TYPE = "analysis"


def _spec(analysis_version: str, spec: AnalysisSpec | None) -> AnalysisSpec:
    return spec or AnalysisSpec()


def candidate_uid(fetch_result: FetchResult) -> str:
    fingerprint = fetch_result.normalized_final_fingerprint or fetch_result.normalized_fingerprint
    return f"site-{fingerprint}"


def document_from_fetch(fetch_result: FetchResult) -> AnalysisDocument:
    if fetch_result.status != "success" or not fetch_result.content_hash:
        raise ValueError("analysis requires a successful immutable fetch result")
    return AnalysisDocument(
        source_uid=fetch_result.result_uid,
        candidate_uid=candidate_uid(fetch_result),
        content_hash=fetch_result.content_hash,
        title=fetch_result.title or fetch_result.og_title or fetch_result.twitter_title,
        description=(
            fetch_result.meta_description
            or fetch_result.og_description
            or fetch_result.twitter_description
        ),
        heading=fetch_result.heading,
        text_excerpt=fetch_result.text_excerpt or "",
        declared_language=fetch_result.language,
    )


def enqueue_analysis_task(
    session: Session,
    *,
    fetch_result: FetchResult,
    run_id: int | None,
    analysis_version: str = "analysis-rules-v1",
    spec: AnalysisSpec | None = None,
    max_attempts: int = 3,
    available_at: datetime | None = None,
) -> EnqueueResult | None:
    spec = _spec(analysis_version, spec)
    key = analysis_key(fetch_result_uid=fetch_result.result_uid, content_hash=fetch_result.content_hash or "", spec=spec)
    existing = session.scalar(
        select(AnalysisResult.id).where(
            AnalysisResult.analysis_key == key,
        )
    )
    if existing is not None:
        return None
    result = enqueue_task(
        session,
        task_type=CONTENT_ANALYSIS_TASK_TYPE,
        target=fetch_result.result_uid,
        payload={
            "schema_version": ANALYSIS_TASK_SCHEMA,
            "fetch_result_uid": fetch_result.result_uid,
            "candidate_uid": candidate_uid(fetch_result),
            "content_hash": fetch_result.content_hash,
            "analysis_version": analysis_version,
            "analysis_key": key,
            "analysis_spec": spec.payload(),
            "task_contract": "content_analysis",
        },
        run_id=run_id,
        dedupe_key=key,
        available_at=available_at,
    )
    if result.created:
        result.task.max_attempts = max_attempts
    return result


def persist_analysis_result(
    session: Session,
    *,
    fetch_result: FetchResult,
    outcome: AnalysisOutcome,
    analysis_version: str,
    spec: AnalysisSpec | None = None,
    task_uid: str | None = None,
    run_uid: str | None = None,
    provider_response: object | None = None,
) -> AnalysisResult:
    spec = _spec(analysis_version, spec)
    key = analysis_key(fetch_result_uid=fetch_result.result_uid, content_hash=outcome.content_hash, spec=spec)
    # Legacy schema also has (fetch_result_id, analysis_version) uniqueness.
    # Keep it compatible while making a changed immutable spec a new version.
    stored_version = f"{analysis_version[:112]}:{key[:15]}"
    existing = session.scalar(
        select(AnalysisResult).where(
            AnalysisResult.analysis_key == key,
        )
    )
    if existing is not None:
        return existing
    snapshot = input_snapshot(title=fetch_result.title or fetch_result.og_title,
        meta_description=fetch_result.meta_description or fetch_result.og_description,
        heading=fetch_result.heading, text_excerpt=fetch_result.text_excerpt,
        normalized_url=fetch_result.normalized_final_url or fetch_result.normalized_url,
        language=fetch_result.language, content_type=fetch_result.content_type,
        content_hash=outcome.content_hash)
    now = utc_now()
    record = AnalysisResult(
        analysis_uid=uuid4().hex,
        fetch_result_id=fetch_result.id,
        candidate_uid=outcome.candidate_uid,
        analysis_version=stored_version,
        analysis_key=key, task_uid=task_uid, run_uid=run_uid,
        normalized_url=snapshot["normalized_url"], analyzer_type=spec.analyzer_type,
        provider_name=spec.provider_name or None, model_version=spec.model_version or None,
        prompt_version=spec.prompt_version, taxonomy_version=spec.taxonomy_version,
        scoring_version=spec.scoring_version, schema_version=spec.schema_version,
        status="completed", quality_reasons_json=[], risk_flags_json=[], risk_reasons_json=[],
        provider_response_sanitized=provider_response if isinstance(provider_response, dict) else outcome.provider_response_sanitized,
        provider_request_hash=sha256(canonical_json(snapshot).encode("utf-8")).hexdigest(),
        input_snapshot_json=snapshot, input_snapshot_hash=sha256(canonical_json(snapshot).encode("utf-8")).hexdigest(),
        started_at=now, completed_at=now,
        content_hash=outcome.content_hash,
        original_language=outcome.original_language,
        detected_language=outcome.detected_language,
        language_confidence=outcome.language_confidence,
        category=outcome.category,
        category_confidence=outcome.category_confidence,
        quality_score=outcome.quality_score,
        title_original=outcome.title_original,
        summary_zh=outcome.summary_zh,
        summary_method=outcome.summary_method,
        tags_json=list(outcome.tags_zh),
        rule_version=outcome.rule_version,
        model_name=outcome.model_name,
        model_status=outcome.model_status,
        model_error_code=outcome.model_error_code,
        evidence_hashes_json=list(outcome.evidence_hashes),
    )
    try:
        with session.begin_nested():
            session.add(record)
            session.flush()
    except IntegrityError:
        existing = session.scalar(
            select(AnalysisResult).where(
                AnalysisResult.analysis_key == key,
            )
        )
        if existing is None:
            raise
        return existing
    return record


def persist_risk_decision(
    session: Session,
    *,
    analysis_result: AnalysisResult,
    assessment: RiskAssessment,
    decision_version: str,
) -> RiskDecision:
    existing = session.scalar(
        select(RiskDecision).where(
            RiskDecision.analysis_result_id == analysis_result.id,
            RiskDecision.decision_version == decision_version,
        )
    )
    if existing is not None:
        return existing
    record = RiskDecision(
        decision_uid=uuid4().hex,
        analysis_result_id=analysis_result.id,
        decision_version=decision_version,
        status=assessment.status,
        risk_score=assessment.risk_score,
        confidence=assessment.confidence,
        hard_reject=assessment.hard_reject,
        rule_codes_json=list(assessment.rule_codes),
        evidence_hashes_json=list(assessment.evidence_hashes),
    )
    try:
        with session.begin_nested():
            session.add(record)
            session.flush()
    except IntegrityError:
        existing = session.scalar(
            select(RiskDecision).where(
                RiskDecision.analysis_result_id == analysis_result.id,
                RiskDecision.decision_version == decision_version,
            )
        )
        if existing is None:
            raise
        return existing
    return record


__all__ = [
    "ANALYSIS_TASK_SCHEMA",
    "CONTENT_ANALYSIS_TASK_TYPE",
    "candidate_uid",
    "document_from_fetch",
    "enqueue_analysis_task",
    "persist_analysis_result",
    "persist_risk_decision",
]
