"""Worker registration and derived liveness state."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.crawler.db import WorkerHeartbeat
from backend.crawler.observability import redact_sensitive


ONLINE = "online"
STALE = "stale"
STOPPED = "stopped"

class WorkerNotFound(LookupError):
    """Raised when heartbeat state is requested for an unknown worker."""


def _validate_identity(
    *,
    worker_id: str,
    worker_type: str,
    process_id: int,
    hostname: str,
) -> tuple[str, str, str]:
    normalized_worker_id = worker_id.strip()
    normalized_worker_type = worker_type.strip()
    normalized_hostname = hostname.strip()
    if not normalized_worker_id:
        raise ValueError("crawler worker ID must not be blank")
    if not normalized_worker_type:
        raise ValueError("crawler worker type must not be blank")
    if process_id <= 0:
        raise ValueError("crawler worker process ID must be positive")
    if not normalized_hostname:
        raise ValueError("crawler worker hostname must not be blank")
    return normalized_worker_id, normalized_worker_type, normalized_hostname


def _find_worker(
    session: Session,
    worker_id: str,
    *,
    lock: bool,
) -> WorkerHeartbeat | None:
    query = select(WorkerHeartbeat).where(
        WorkerHeartbeat.worker_id == worker_id
    )
    if lock:
        query = query.with_for_update()
    return session.scalar(query)


def _required_worker(
    session: Session,
    worker_id: str,
) -> WorkerHeartbeat:
    worker = _find_worker(session, worker_id, lock=True)
    if worker is None:
        raise WorkerNotFound("crawler worker was not found")
    return worker


def register_worker(
    session: Session,
    *,
    worker_id: str,
    worker_type: str,
    process_id: int,
    hostname: str,
    now: datetime,
    metadata: dict[str, Any] | None = None,
) -> WorkerHeartbeat:
    normalized_worker_id, normalized_worker_type, normalized_hostname = (
        _validate_identity(
            worker_id=worker_id,
            worker_type=worker_type,
            process_id=process_id,
            hostname=hostname,
        )
    )
    worker = _find_worker(session, normalized_worker_id, lock=True)
    if worker is None:
        worker = WorkerHeartbeat(
            worker_id=normalized_worker_id,
            worker_type=normalized_worker_type,
            process_id=process_id,
            hostname=normalized_hostname,
            status=ONLINE,
            current_task_uid=None,
            started_at=now,
            last_seen_at=now,
            metadata_json=(
                redact_sensitive(metadata) if metadata is not None else None
            ),
        )
        try:
            with session.begin_nested():
                session.add(worker)
                session.flush()
        except IntegrityError:
            worker = _find_worker(session, normalized_worker_id, lock=True)
            if worker is None:
                raise

    worker.worker_type = normalized_worker_type
    worker.process_id = process_id
    worker.hostname = normalized_hostname
    worker.status = ONLINE
    worker.current_task_uid = None
    worker.started_at = now
    worker.last_seen_at = now
    if metadata is not None:
        worker.metadata_json = redact_sensitive(metadata)
    session.flush()
    return worker


def heartbeat_worker(
    session: Session,
    *,
    worker_id: str,
    now: datetime,
    current_task_uid: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> WorkerHeartbeat:
    worker = _required_worker(session, worker_id.strip())
    worker.last_seen_at = now
    if worker.status != STOPPED:
        worker.status = ONLINE
        worker.current_task_uid = current_task_uid
    else:
        worker.current_task_uid = None
    if metadata is not None:
        worker.metadata_json = redact_sensitive(metadata)
    session.flush()
    return worker


def mark_worker_stopped(
    session: Session,
    *,
    worker_id: str,
    now: datetime,
) -> WorkerHeartbeat:
    worker = _required_worker(session, worker_id.strip())
    worker.status = STOPPED
    worker.current_task_uid = None
    worker.last_seen_at = now
    session.flush()
    return worker


def worker_effective_status(
    worker: WorkerHeartbeat,
    *,
    now: datetime,
    stale_after_seconds: int,
) -> str:
    if stale_after_seconds <= 0:
        raise ValueError("crawler stale threshold must be positive")
    if worker.status == STOPPED:
        return STOPPED
    if now > worker.last_seen_at + timedelta(seconds=stale_after_seconds):
        return STALE
    return ONLINE
