"""Application-level permanent URL identity inside one crawl run."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.crawler.db import CrawlTask
from backend.crawler.queue.tasks import EnqueueResult, enqueue_task, task_target_hash


def enqueue_discovered_task(
    session: Session,
    *,
    task_type: str,
    target: str,
    payload: dict,
    run_id: int | None,
    priority: int = 100,
) -> EnqueueResult:
    target_hash = task_target_hash(target)
    query = select(CrawlTask).where(
        CrawlTask.task_type == task_type,
        CrawlTask.target_hash == target_hash,
    )
    if run_id is not None:
        existing = session.scalar(query.where(CrawlTask.run_id == run_id))
    else:
        run_uid = payload.get("run_uid")
        existing = next(
            (
                task
                for task in session.scalars(query.where(CrawlTask.run_id.is_(None))).all()
                if isinstance(task.payload_json, dict)
                and task.payload_json.get("run_uid") == run_uid
            ),
            None,
        )
    if existing is not None:
        return EnqueueResult(existing, False)
    return enqueue_task(
        session,
        task_type=task_type,
        target=target,
        payload=payload,
        run_id=run_id,
        priority=priority,
        dedupe_key=target,
    )


__all__ = ["enqueue_discovered_task"]
