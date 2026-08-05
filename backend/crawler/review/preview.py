"""Crawler-local preview snapshots and side-effect-free duplicate utilities."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Iterable, Mapping
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.crawler.db import PublishPreview as StoredPublishPreview, ReviewCase
from backend.crawler.db.base import utc_now
from backend.crawler.net.url import InvalidUrl, normalize_http_url
from backend.crawler.review.service import mark_publish_ready, review_content_hash
from backend.crawler.review.states import APPROVED, PUBLISH_READY


@dataclass(frozen=True, slots=True)
class PublishPreview:
    result: str
    matches: tuple[dict[str, object], ...]

    def payload(self) -> dict[str, object]:
        return asdict(self)


def local_preview_payload(case: ReviewCase) -> dict[str, object]:
    """Serialize selected review values only; this never queries nav_site."""
    return {"result": "local_validation_only", "matches": [], "review": {
        "title": case.selected_title, "url": case.selected_url,
        "category": case.selected_category, "summary": case.selected_summary,
        "tags": case.selected_tags, "risk_level": case.selected_risk_level,
        "quality_score": case.selected_quality_score,
    }}


def create_local_preview(session: Session, case: ReviewCase, *, expected_version: int, actor_id: str, ttl_seconds: int = 3600) -> tuple[ReviewCase, StoredPublishPreview]:
    """Persist a version-bound preview without opening a target connection."""
    if case.status == APPROVED:
        case = mark_publish_ready(session, case, expected_version=expected_version, actor_id=actor_id)
    elif case.status != PUBLISH_READY:
        raise ValueError("only an approved review may receive a publish preview")
    content_hash = case.review_content_hash or review_content_hash(case)
    existing = session.scalar(select(StoredPublishPreview).where(
        StoredPublishPreview.review_case_id == case.id,
        StoredPublishPreview.review_version == case.version,
        StoredPublishPreview.content_hash == content_hash,
    ))
    if existing is not None:
        return case, existing
    now = utc_now()
    preview = StoredPublishPreview(
        preview_uid=uuid4().hex, review_case_id=case.id, review_version=case.version,
        content_hash=content_hash, result_json=local_preview_payload(case),
        generated_by=str(actor_id)[:128], generated_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    session.add(preview)
    session.flush()
    return case, preview


def _site_value(site: Mapping[str, object] | object, name: str) -> object | None:
    return site.get(name) if isinstance(site, Mapping) else getattr(site, name, None)


def detect_duplicates(url: str, existing_sites: Iterable[Mapping[str, object] | object]) -> PublishPreview:
    """Classify exact, canonical, domain, and multi-match conflicts without writes."""
    selected = normalize_http_url(url)
    exact: list[dict[str, object]] = []
    canonical: list[dict[str, object]] = []
    domain: list[dict[str, object]] = []
    for site in existing_sites:
        candidate = str(_site_value(site, "url") or "").strip()
        if not candidate:
            continue
        item = {"id": _site_value(site, "id"), "name": _site_value(site, "name"), "url": candidate}
        if candidate == selected.raw_url.strip():
            exact.append(item)
            continue
        try:
            normalized = normalize_http_url(candidate)
        except InvalidUrl:
            continue
        if normalized.url == selected.url:
            canonical.append(item)
        elif normalized.hostname == selected.hostname:
            domain.append(item)
    kinds = sum(bool(group) for group in (exact, canonical, domain))
    if kinds > 1 or len(exact) > 1 or len(canonical) > 1:
        return PublishPreview("conflict", tuple(exact + canonical + domain))
    if exact:
        return PublishPreview("exact_match", tuple(exact))
    if canonical:
        return PublishPreview("canonical_match", tuple(canonical))
    if domain:
        return PublishPreview("domain_match", tuple(domain))
    return PublishPreview("no_match", ())
