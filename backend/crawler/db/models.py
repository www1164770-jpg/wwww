"""Crawler-owned Phase 1 through Phase 3 tables.

Status strings are validated by service modules rather than database ENUMs so
SQLite tests and MySQL production share the same transition semantics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    BigInteger,
    Boolean,
    ForeignKey,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import BIGINT_ID, CrawlerBase, utc_now


class CrawlRun(CrawlerBase):
    __tablename__ = "crawl_runs"
    __table_args__ = (
        UniqueConstraint("run_uid", name="uq_crawl_runs_run_uid"),
        Index("ix_crawl_runs_status_scheduled", "status", "scheduled_for"),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    run_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    stop_requested_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    target_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leased_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class CrawlTask(CrawlerBase):
    __tablename__ = "crawl_tasks"
    __table_args__ = (
        UniqueConstraint("task_uid", name="uq_crawl_tasks_task_uid"),
        UniqueConstraint(
            "task_type",
            "active_dedupe_key",
            name="uq_crawl_tasks_active_dedupe",
        ),
        Index(
            "ix_crawl_tasks_lease_candidates",
            "status",
            "available_at",
            "priority",
            "created_at",
        ),
        Index(
            "ix_crawl_tasks_expired_leases",
            "status",
            "leased_until",
        ),
        Index("ix_crawl_tasks_run_status", "run_id", "status"),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    task_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    run_id: Mapped[int | None] = mapped_column(
        BIGINT_ID,
        ForeignKey("crawl_runs.id", ondelete="SET NULL"),
    )
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    target_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(64), nullable=False)
    active_dedupe_key: Mapped[str | None] = mapped_column(String(64))
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    available_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    leased_at: Mapped[datetime | None] = mapped_column(DateTime)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime)
    worker_id: Mapped[str | None] = mapped_column(String(128))
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    last_error_message: Mapped[str | None] = mapped_column(String(1000))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class WorkerHeartbeat(CrawlerBase):
    __tablename__ = "worker_heartbeats"
    __table_args__ = (
        UniqueConstraint("worker_id", name="uq_worker_heartbeats_worker_id"),
        Index(
            "ix_worker_heartbeats_status_seen",
            "status",
            "last_seen_at",
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    worker_id: Mapped[str] = mapped_column(String(128), nullable=False)
    worker_type: Mapped[str] = mapped_column(String(64), nullable=False)
    process_id: Mapped[int] = mapped_column(Integer, nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_task_uid: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class CrawlerSetting(CrawlerBase):
    __tablename__ = "crawler_settings"

    setting_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class OutboxEvent(CrawlerBase):
    __tablename__ = "outbox_events"
    __table_args__ = (
        UniqueConstraint("event_uid", name="uq_outbox_events_event_uid"),
        Index(
            "ix_outbox_events_lease_candidates",
            "status",
            "available_at",
            "created_at",
        ),
        Index(
            "ix_outbox_events_expired_leases",
            "status",
            "leased_until",
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    event_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    available_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    leased_at: Mapped[datetime | None] = mapped_column(DateTime)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime)
    worker_id: Mapped[str | None] = mapped_column(String(128))
    last_error: Mapped[str | None] = mapped_column(String(1000))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class FetchResult(CrawlerBase):
    __tablename__ = "fetch_results"
    __table_args__ = (
        UniqueConstraint("result_uid", name="uq_fetch_results_result_uid"),
        UniqueConstraint("task_id", name="uq_fetch_results_task_id"),
        UniqueConstraint(
            "normalized_final_fingerprint",
            "content_hash",
            name="uq_fetch_results_final_content",
        ),
        Index("ix_fetch_results_status_fetched", "status", "fetched_at"),
        Index(
            "ix_fetch_results_final_fetched",
            "normalized_final_fingerprint",
            "fetched_at",
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    result_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    task_id: Mapped[int | None] = mapped_column(
        BIGINT_ID,
        ForeignKey("crawl_tasks.id"),
    )
    requested_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    final_url: Mapped[str | None] = mapped_column(Text)
    normalized_final_url: Mapped[str | None] = mapped_column(Text)
    normalized_final_fingerprint: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer)
    content_type: Mapped[str | None] = mapped_column(String(255))
    charset: Mapped[str | None] = mapped_column(String(64))
    bytes_read: Mapped[int | None] = mapped_column(BigInteger)
    redirect_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    redirect_chain: Mapped[list[Any] | None] = mapped_column(JSON)
    title: Mapped[str | None] = mapped_column(String(500))
    meta_description: Mapped[str | None] = mapped_column(Text)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    og_title: Mapped[str | None] = mapped_column(String(500))
    og_description: Mapped[str | None] = mapped_column(Text)
    og_image_url: Mapped[str | None] = mapped_column(Text)
    twitter_title: Mapped[str | None] = mapped_column(String(500))
    twitter_description: Mapped[str | None] = mapped_column(Text)
    twitter_image_url: Mapped[str | None] = mapped_column(Text)
    favicon_url: Mapped[str | None] = mapped_column(Text)
    apple_touch_icon_url: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(64))
    heading: Mapped[str | None] = mapped_column(String(1000))
    text_excerpt: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    document_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    robots_allowed: Mapped[bool | None] = mapped_column(Boolean)
    robots_status: Mapped[int | None] = mapped_column(Integer)
    etag: Mapped[str | None] = mapped_column(String(500))
    last_modified: Mapped[str | None] = mapped_column(String(500))
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    elapsed_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message_sanitized: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class DiscoveredLink(CrawlerBase):
    __tablename__ = "discovered_links"
    __table_args__ = (
        UniqueConstraint("link_uid", name="uq_discovered_links_link_uid"),
        UniqueConstraint(
            "source_result_id",
            "normalized_fingerprint",
            name="uq_discovered_links_source_url",
        ),
        Index("ix_discovered_links_normalized", "normalized_fingerprint"),
        Index("ix_discovered_links_enqueue", "enqueue_status", "discovered_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    link_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    source_result_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("fetch_results.id"),
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    discovered_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    discovery_type: Mapped[str] = mapped_column(String(64), nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    is_safe: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_same_origin: Mapped[bool] = mapped_column(Boolean, nullable=False)
    enqueue_status: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AnalysisResult(CrawlerBase):
    __tablename__ = "analysis_results"
    __table_args__ = (
        UniqueConstraint("analysis_uid", name="uq_analysis_results_uid"),
        UniqueConstraint("analysis_key", name="uq_analysis_results_key"),
        UniqueConstraint(
            "fetch_result_id",
            "analysis_version",
            name="uq_analysis_results_fetch_version",
        ),
        Index("ix_analysis_results_candidate_created", "candidate_uid", "created_at"),
        Index("ix_analysis_results_category_confidence", "category", "category_confidence"),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    analysis_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    fetch_result_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("fetch_results.id"),
        nullable=False,
    )
    candidate_uid: Mapped[str] = mapped_column(String(72), nullable=False)
    analysis_version: Mapped[str] = mapped_column(String(128), nullable=False)
    analysis_key: Mapped[str | None] = mapped_column(String(64))
    task_uid: Mapped[str | None] = mapped_column(String(64))
    run_uid: Mapped[str | None] = mapped_column(String(64))
    normalized_url: Mapped[str | None] = mapped_column(Text)
    analyzer_type: Mapped[str | None] = mapped_column(String(32))
    provider_name: Mapped[str | None] = mapped_column(String(128))
    model_version: Mapped[str | None] = mapped_column(String(128))
    prompt_version: Mapped[str | None] = mapped_column(String(128))
    taxonomy_version: Mapped[str | None] = mapped_column(String(128))
    scoring_version: Mapped[str | None] = mapped_column(String(128))
    schema_version: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str | None] = mapped_column(String(32))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    original_language: Mapped[str | None] = mapped_column(String(64))
    detected_language: Mapped[str] = mapped_column(String(16), nullable=False)
    language_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    category_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_reasons_json: Mapped[list[Any] | None] = mapped_column(JSON)
    risk_level: Mapped[str | None] = mapped_column(String(16))
    risk_flags_json: Mapped[list[Any] | None] = mapped_column(JSON)
    risk_reasons_json: Mapped[list[Any] | None] = mapped_column(JSON)
    title_original: Mapped[str | None] = mapped_column(String(500))
    summary_zh: Mapped[str] = mapped_column(Text, nullable=False)
    summary_method: Mapped[str] = mapped_column(String(32), nullable=False)
    tags_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(255))
    model_status: Mapped[str] = mapped_column(String(32), nullable=False)
    model_error_code: Mapped[str | None] = mapped_column(String(64))
    subcategory_suggestion: Mapped[str | None] = mapped_column(String(64))
    provider_response_sanitized: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    provider_request_hash: Mapped[str | None] = mapped_column(String(64))
    input_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    input_snapshot_hash: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message_sanitized: Mapped[str | None] = mapped_column(Text)
    evidence_hashes_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class RiskDecision(CrawlerBase):
    __tablename__ = "risk_decisions"
    __table_args__ = (
        UniqueConstraint("decision_uid", name="uq_risk_decisions_uid"),
        UniqueConstraint(
            "analysis_result_id",
            "decision_version",
            name="uq_risk_decisions_analysis_version",
        ),
        Index("ix_risk_decisions_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    decision_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    analysis_result_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("analysis_results.id"),
        nullable=False,
    )
    decision_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    hard_reject: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rule_codes_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    evidence_hashes_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)


class IconAsset(CrawlerBase):
    __tablename__ = "icon_assets"
    __table_args__ = (
        UniqueConstraint("asset_uid", name="uq_icon_assets_uid"),
        UniqueConstraint("content_hash", name="uq_icon_assets_content_hash"),
        Index("ix_icon_assets_fetch_result", "fetch_result_id", "fetched_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    asset_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    fetch_result_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("fetch_results.id"),
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    relative_path: Mapped[str] = mapped_column(String(500), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ReviewCase(CrawlerBase):
    __tablename__ = "review_cases"
    __table_args__ = (
        UniqueConstraint("review_uid", name="uq_review_cases_uid"),
        Index("ix_review_cases_analysis", "analysis_result_id"),
        Index("ix_review_cases_status_created", "status", "created_at"),
        Index("ix_review_cases_priority", "priority", "created_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    review_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    fetch_result_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("fetch_results.id"),
        nullable=False,
    )
    analysis_result_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("analysis_results.id"),
        nullable=False,
    )
    source_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_analysis_uid: Mapped[str | None] = mapped_column(String(64))
    source_analysis_version: Mapped[str | None] = mapped_column(String(128))
    source_input_snapshot_hash: Mapped[str | None] = mapped_column(String(64))
    source_analyzer_type: Mapped[str | None] = mapped_column(String(32))
    source_model_version: Mapped[str | None] = mapped_column(String(128))
    source_prompt_version: Mapped[str | None] = mapped_column(String(128))
    source_taxonomy_version: Mapped[str | None] = mapped_column(String(128))
    source_scoring_version: Mapped[str | None] = mapped_column(String(128))
    review_content_hash: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    assigned_reviewer_id: Mapped[str | None] = mapped_column(String(128))
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    decision_at: Mapped[datetime | None] = mapped_column(DateTime)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime)
    publish_ready_at: Mapped[datetime | None] = mapped_column(DateTime)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    selected_title: Mapped[str | None] = mapped_column(String(500))
    selected_summary: Mapped[str | None] = mapped_column(Text)
    selected_description: Mapped[str | None] = mapped_column(Text)
    selected_category: Mapped[str | None] = mapped_column(String(64))
    selected_region: Mapped[str | None] = mapped_column(String(32))
    selected_language: Mapped[str | None] = mapped_column(String(16))
    selected_tags: Mapped[list[Any] | None] = mapped_column(JSON)
    selected_risk_level: Mapped[str | None] = mapped_column(String(16))
    selected_quality_score: Mapped[float | None] = mapped_column(Float)
    selected_url: Mapped[str | None] = mapped_column(Text)
    selected_logo_asset_id: Mapped[int | None] = mapped_column(
        BIGINT_ID,
        ForeignKey("icon_assets.id"),
    )
    risk_acknowledgements: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    override_reasons: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class ReviewEvent(CrawlerBase):
    __tablename__ = "review_events"
    __table_args__ = (
        UniqueConstraint("event_uid", name="uq_review_events_uid"),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    event_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    review_case_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("review_cases.id"),
        nullable=False,
    )
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    publish_uid: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(64))
    review_version: Mapped[int | None] = mapped_column(Integer)
    changed_fields_json: Mapped[list[Any] | None] = mapped_column(JSON)
    previous_status: Mapped[str | None] = mapped_column(String(32))
    next_status: Mapped[str | None] = mapped_column(String(32))
    reason_code: Mapped[str | None] = mapped_column(String(64))
    notes_sanitized: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )


class PublishRecord(CrawlerBase):
    __tablename__ = "publish_records"
    __table_args__ = (
        UniqueConstraint("publish_uid", name="uq_publish_records_uid"),
        UniqueConstraint("idempotency_key", name="uq_publish_records_idempotency"),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    publish_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    review_case_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("review_cases.id"),
        nullable=False,
    )
    review_version: Mapped[int | None] = mapped_column(Integer)
    preview_uid: Mapped[str | None] = mapped_column(String(64))
    target_name: Mapped[str | None] = mapped_column(String(64))
    target_database: Mapped[str] = mapped_column(String(64), nullable=False)
    target_table: Mapped[str] = mapped_column(String(64), nullable=False)
    target_record_id: Mapped[int | None] = mapped_column(BIGINT_ID)
    target_website_id: Mapped[int | None] = mapped_column(Integer)
    target_record_key: Mapped[str | None] = mapped_column(String(128))
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    target_before_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    target_after_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    last_error_sanitized: Mapped[str | None] = mapped_column(Text)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class PublishPreview(CrawlerBase):
    __tablename__ = "publish_previews"
    __table_args__ = (
        UniqueConstraint("preview_uid", name="uq_publish_previews_uid"),
        UniqueConstraint("review_case_id", "review_version", "content_hash", name="uq_publish_previews_review_version_hash"),
        Index("ix_publish_previews_review_valid", "review_case_id", "invalidated_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True, autoincrement=True)
    preview_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    review_case_id: Mapped[int] = mapped_column(BIGINT_ID, ForeignKey("review_cases.id"), nullable=False)
    review_version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(128), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime)
    invalidated_reason: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
