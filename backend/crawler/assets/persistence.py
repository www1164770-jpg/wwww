"""Idempotent icon tasks and crawler-owned asset metadata."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.crawler.db import FetchResult, IconAsset
from backend.crawler.queue.tasks import EnqueueResult, enqueue_task

from .icons import StoredIcon


ICON_TASK_SCHEMA = "phase3-icon-task-v1"


def enqueue_icon_task(
    session: Session,
    *,
    fetch_result: FetchResult,
    source_url: str | None,
    run_id: int | None,
    max_attempts: int = 3,
    available_at: datetime | None = None,
) -> EnqueueResult | None:
    if not source_url:
        return None
    existing = session.scalar(
        select(IconAsset.id).where(IconAsset.fetch_result_id == fetch_result.id)
    )
    if existing is not None:
        return None
    result = enqueue_task(
        session,
        task_type="icon_fetch",
        target=source_url,
        payload={
            "schema_version": ICON_TASK_SCHEMA,
            "fetch_result_uid": fetch_result.result_uid,
        },
        run_id=run_id,
        dedupe_key=f"{fetch_result.result_uid}:icon-v1",
        available_at=available_at,
    )
    if result.created:
        result.task.max_attempts = max_attempts
    return result


def persist_icon_asset(
    session: Session,
    *,
    fetch_result: FetchResult,
    stored: StoredIcon,
    fetched_at: datetime,
) -> IconAsset:
    existing = session.scalar(
        select(IconAsset).where(IconAsset.content_hash == stored.content_hash)
    )
    if existing is not None:
        return existing
    record = IconAsset(
        asset_uid=uuid4().hex,
        fetch_result_id=fetch_result.id,
        source_url=stored.source_url,
        content_hash=stored.content_hash,
        mime_type=stored.mime_type,
        width=stored.width,
        height=stored.height,
        byte_size=stored.byte_size,
        relative_path=stored.relative_path,
        fetched_at=fetched_at,
    )
    try:
        with session.begin_nested():
            session.add(record)
            session.flush()
    except IntegrityError:
        existing = session.scalar(
            select(IconAsset).where(IconAsset.content_hash == stored.content_hash)
        )
        if existing is None:
            raise
        return existing
    return record


__all__ = ["ICON_TASK_SCHEMA", "enqueue_icon_task", "persist_icon_asset"]
