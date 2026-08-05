"""Idempotent persistence for static fetch results and discovered links."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.crawler.db import CrawlTask, DiscoveredLink, FetchResult
from backend.crawler.discovery.html import HtmlDocument
from backend.crawler.discovery.links import DiscoveredCandidate
from backend.crawler.net.url import normalize_http_url
from backend.crawler.observability import sanitize_error_code, sanitize_error_message
from backend.crawler.net.url import InvalidUrl, safe_url_for_output

from .http import HttpFetchResult


@dataclass(frozen=True, slots=True)
class PersistResult:
    result: FetchResult
    created: bool
    updated: bool


def _document_values(document: HtmlDocument | None) -> dict[str, object]:
    if document is None:
        return {
            "title": None,
            "meta_description": None,
            "canonical_url": None,
            "og_title": None,
            "og_description": None,
            "og_image_url": None,
            "twitter_title": None,
            "twitter_description": None,
            "twitter_image_url": None,
            "favicon_url": None,
            "apple_touch_icon_url": None,
            "language": None,
            "heading": None,
            "text_excerpt": None,
        }
    return {
        "title": document.title,
        "meta_description": document.meta_description,
        "canonical_url": document.canonical_url,
        "og_title": document.og_title,
        "og_description": document.og_description,
        "og_image_url": document.og_image_url,
        "twitter_title": document.twitter_title,
        "twitter_description": document.twitter_description,
        "twitter_image_url": document.twitter_image_url,
        "favicon_url": document.favicon_url,
        "apple_touch_icon_url": document.apple_touch_icon_url,
        "language": document.language,
        "heading": document.heading,
        "text_excerpt": document.text_excerpt,
    }


def persist_fetch_result(
    session: Session,
    *,
    task: CrawlTask,
    fetch: HttpFetchResult,
    document: HtmlDocument | None,
    fetched_at: datetime,
    document_metadata: dict | None = None,
) -> PersistResult:
    requested = normalize_http_url(fetch.normalized_url)
    final = normalize_http_url(fetch.final_url)
    content_hash = document.content_hash if document is not None else sha256(fetch.body).hexdigest()
    existing_task = session.scalar(select(FetchResult).where(FetchResult.task_id == task.id))
    if existing_task is not None and existing_task.content_hash == content_hash and existing_task.status == "success":
        return PersistResult(existing_task, False, False)
    unchanged = session.scalar(
        select(FetchResult).where(
            FetchResult.normalized_final_fingerprint == final.fingerprint,
            FetchResult.content_hash == content_hash,
        )
    )
    if unchanged is not None and unchanged is not existing_task:
        return PersistResult(unchanged, False, False)

    robots = fetch.robots
    values = {
        "requested_url": fetch.requested_url,
        "normalized_url": requested.url,
        "normalized_fingerprint": requested.fingerprint,
        "final_url": fetch.final_url,
        "normalized_final_url": final.url,
        "normalized_final_fingerprint": final.fingerprint,
        "status": "success",
        "http_status": fetch.status_code,
        "content_type": fetch.content_type,
        "charset": fetch.charset,
        "bytes_read": fetch.bytes_read,
        "redirect_count": len(fetch.redirect_chain),
        "redirect_chain": list(fetch.redirect_chain),
        "content_hash": content_hash,
        "document_metadata_json": document_metadata,
        "robots_allowed": robots.allowed if robots is not None else None,
        "robots_status": robots.status_code if robots is not None else None,
        "etag": fetch.etag,
        "last_modified": fetch.last_modified,
        "fetched_at": fetched_at,
        "elapsed_ms": fetch.elapsed_ms,
        "error_code": None,
        "error_message_sanitized": None,
        "updated_at": fetched_at,
        **_document_values(document),
    }
    if existing_task is not None:
        for name, value in values.items():
            setattr(existing_task, name, value)
        session.flush()
        return PersistResult(existing_task, False, True)

    result = FetchResult(
        result_uid=uuid4().hex,
        task_id=task.id,
        created_at=fetched_at,
        **values,
    )
    try:
        with session.begin_nested():
            session.add(result)
            session.flush()
    except IntegrityError:
        existing = session.scalar(
            select(FetchResult).where(
                FetchResult.normalized_final_fingerprint == final.fingerprint,
                FetchResult.content_hash == content_hash,
            )
        )
        if existing is None:
            raise
        return PersistResult(existing, False, False)
    return PersistResult(result, True, False)


def persist_discovered_links(
    session: Session,
    *,
    result: FetchResult,
    links: tuple[DiscoveredCandidate, ...],
    discovered_at: datetime,
) -> int:
    created = 0
    for link in links:
        normalized = normalize_http_url(link.normalized_url)
        existing = session.scalar(
            select(DiscoveredLink.id).where(
                DiscoveredLink.source_result_id == result.id,
                DiscoveredLink.normalized_fingerprint == normalized.fingerprint,
            )
        )
        if existing is not None:
            continue
        record = DiscoveredLink(
            link_uid=uuid4().hex,
            source_result_id=result.id,
            source_url=result.normalized_final_url or result.normalized_url,
            discovered_url=link.discovered_url,
            normalized_url=normalized.url,
            normalized_fingerprint=normalized.fingerprint,
            relation_type=link.relation_type,
            discovery_type=link.discovery_type,
            depth=link.depth,
            is_safe=True,
            is_same_origin=link.same_origin,
            enqueue_status="queued" if link.enqueue else "recorded",
            metadata_json=dict(link.metadata),
            discovered_at=discovered_at,
        )
        try:
            with session.begin_nested():
                session.add(record)
                session.flush()
        except IntegrityError:
            continue
        created += 1
    return created


def persist_fetch_failure(
    session: Session,
    *,
    task: CrawlTask,
    target_url: str,
    error_code: str,
    error_message: str,
    fetched_at: datetime,
    http_status: int | None = None,
) -> FetchResult:
    try:
        normalized = normalize_http_url(target_url)
        stored_url = normalized.url
        fingerprint = normalized.fingerprint
    except (InvalidUrl, ValueError):
        stored_url = safe_url_for_output(target_url)
        fingerprint = sha256(stored_url.encode("utf-8")).hexdigest()
    existing = session.scalar(select(FetchResult).where(FetchResult.task_id == task.id))
    values = {
        "requested_url": stored_url,
        "normalized_url": stored_url,
        "normalized_fingerprint": fingerprint,
        "final_url": None,
        "normalized_final_url": None,
        "normalized_final_fingerprint": None,
        "status": "failed",
        "http_status": http_status,
        "content_type": None,
        "charset": None,
        "bytes_read": None,
        "redirect_count": 0,
        "redirect_chain": [],
        "content_hash": None,
        "document_metadata_json": None,
        "robots_allowed": False if error_code == "robots_denied" else None,
        "robots_status": http_status if error_code == "robots_denied" else None,
        "etag": None,
        "last_modified": None,
        "fetched_at": fetched_at,
        "elapsed_ms": None,
        "error_code": sanitize_error_code(error_code),
        "error_message_sanitized": sanitize_error_message(error_message),
        "updated_at": fetched_at,
        **_document_values(None),
    }
    if existing is None:
        existing = FetchResult(
            result_uid=uuid4().hex,
            task_id=task.id,
            created_at=fetched_at,
            **values,
        )
        session.add(existing)
    else:
        for name, value in values.items():
            setattr(existing, name, value)
    session.flush()
    return existing


__all__ = [
    "PersistResult",
    "persist_discovered_links",
    "persist_fetch_failure",
    "persist_fetch_result",
]
