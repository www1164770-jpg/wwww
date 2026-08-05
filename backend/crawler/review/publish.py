"""Explicit, idempotent publish orchestration; never opens a nav-site connection."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.crawler.db import PublishPreview as StoredPublishPreview, PublishRecord, ReviewCase
from backend.crawler.db.base import utc_now
from backend.crawler.review.mapping import WebsiteFields
from backend.crawler.review.preview import PublishPreview, detect_duplicates
from backend.crawler.review.service import mark_publish_failed, mark_published, mark_publishing
from backend.crawler.review.states import PUBLISH_FAILED, PUBLISH_READY, PUBLISHED


class NavSitePublisher(Protocol):
    """Adapter boundary: application code must opt in to nav-site synchronization."""
    def list_sites(self) -> list[object]: ...
    def create_website(self, fields: WebsiteFields) -> object: ...


class PublishUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PublishOutcome:
    record: PublishRecord
    preview: PublishPreview
    published: bool


def publish_preview(fields: WebsiteFields, publisher: NavSitePublisher) -> PublishPreview:
    return detect_duplicates(fields.url, publisher.list_sites())


def _idempotency_key(case: ReviewCase, fields: WebsiteFields, preview: StoredPublishPreview | None = None) -> str:
    # The review version changes when publishing reaches ``published``.  It must
    # not change the idempotency identity of an otherwise identical retry.
    preview_identity = f":{preview.review_version}:{preview.content_hash}" if preview else ""
    payload = f"review-publish-v1:{case.review_uid}:{case.source_content_hash}{preview_identity}:{fields.snapshot()}"
    return sha256(payload.encode("utf-8")).hexdigest()


def _validate_stored_preview(case: ReviewCase, preview: StoredPublishPreview) -> None:
    now = utc_now()
    if preview.review_case_id != case.id or preview.invalidated_at is not None:
        raise PermissionError("publish preview is invalidated")
    if preview.expires_at is not None and preview.expires_at <= now:
        raise PermissionError("publish preview has expired")
    if preview.content_hash != case.review_content_hash:
        raise PermissionError("publish preview does not match the review content")
    if preview.review_version > case.version:
        raise PermissionError("publish preview has an invalid review version")


def execute_publish(session: Session, *, case: ReviewCase, fields: WebsiteFields, publisher: NavSitePublisher | None, confirmed: bool, actor_id: str, expected_version: int, stored_preview: StoredPublishPreview | None = None, max_retries: int = 3) -> PublishOutcome:
    """Publish only after an explicit confirmation and a fresh duplicate check."""
    if not confirmed:
        raise PermissionError("publishing requires explicit confirmation")
    if publisher is None:
        raise PublishUnavailable("nav-site synchronization is not configured")
    if stored_preview is not None:
        _validate_stored_preview(case, stored_preview)
    key = _idempotency_key(case, fields, stored_preview)
    existing = session.scalar(select(PublishRecord).where(PublishRecord.idempotency_key == key))
    if existing is not None and existing.status == "published":
        return PublishOutcome(existing, PublishPreview("exact_match", ()), True)
    modern_target = all(hasattr(publisher, name) for name in ("validate_configuration", "publish", "find_by_idempotency_key"))
    if modern_target:
        publisher.validate_configuration()
        preview = PublishPreview("no_match", ())
    else:
        preview = publish_preview(fields, publisher)
    if existing is None:
        record = PublishRecord(publish_uid=uuid4().hex, review_case_id=case.id, review_version=stored_preview.review_version if stored_preview else case.version, preview_uid=stored_preview.preview_uid if stored_preview else None, target_name="nav_site", target_database="nav_site", target_table="websites", operation_type="insert", idempotency_key=key, source_snapshot=fields.snapshot(), status="publishing", attempt_count=1, started_at=utc_now(), last_attempt_at=utc_now())
        session.add(record)
        session.flush()
    else:
        record = existing
        if record.attempt_count >= max_retries:
            record.status, record.last_error_code = "failed_terminal", "retry_limit_reached"
            return PublishOutcome(record, PublishPreview("no_match", ()), False)
        record.status = "publishing"
        record.attempt_count += 1
        record.started_at = record.last_attempt_at = utc_now()
        record.last_error_code = None
        record.last_error_sanitized = None
        record.next_retry_at = None
    if case.status == PUBLISHED:
        record.status, record.completed_at = "published", utc_now()
        return PublishOutcome(record, preview, True)
    if case.status not in {PUBLISH_READY, PUBLISH_FAILED}:
        record.status, record.completed_at, record.last_error_code = "rejected", utc_now(), "review_not_publish_ready"
        return PublishOutcome(record, preview, False)
    if preview.result != "no_match":
        record.status, record.completed_at, record.last_error_code = "duplicate", utc_now(), preview.result
        return PublishOutcome(record, preview, False)
    try:
        if case.status != PUBLISHED:
            case = mark_publishing(session, case, expected_version=expected_version, actor_id=actor_id, actor_type="admin")
        if modern_target:
            from backend.crawler.review.targets import PublishCommand
            target = publisher.find_by_idempotency_key(key) or publisher.publish(PublishCommand(key, fields))
            target_id = target.target_record_id
        else:
            target = publisher.create_website(fields)
            target_id = getattr(target, "id", None)
            if target_id is None and isinstance(target, dict):
                target_id = target.get("id")
        record.target_record_id = int(target_id) if target_id is not None else None
        record.target_website_id = int(target_id) if target_id is not None else None
        record.target_after_snapshot = fields.snapshot()
        record.target_record_key = key
        record.status, record.completed_at = "published", utc_now()
        mark_published(session, case, expected_version=case.version, actor_id=actor_id, actor_type="admin")
        return PublishOutcome(record, preview, True)
    except Exception:
        from datetime import timedelta
        record.status, record.completed_at, record.last_error_code = "failed_retryable", utc_now(), "sync_failed"
        record.last_error_sanitized = "navigation-site synchronization failed"
        record.next_retry_at = utc_now() + timedelta(seconds=min(3600, 5 * (2 ** max(0, record.attempt_count - 1))))
        if case.status == "publishing":
            mark_publish_failed(session, case, expected_version=case.version, actor_id=actor_id)
        return PublishOutcome(record, preview, False)
