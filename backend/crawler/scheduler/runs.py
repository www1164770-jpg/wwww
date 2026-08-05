"""Persistent crawl-run lifecycle and stop-request boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.crawler.db import CrawlRun


RUNNING = "running"
STOP_REQUESTED = "stop_requested"
COMPLETED = "completed"
FAILED = "failed"
CANCELLED = "cancelled"

ACTIVE_RUN_STATUSES = frozenset({RUNNING, STOP_REQUESTED})
TERMINAL_RUN_STATUSES = frozenset({COMPLETED, FAILED, CANCELLED})


class RunStateError(ValueError):
    """Raised when a crawl run transition is invalid."""


class RunNotFound(LookupError):
    """Raised when a requested crawl run does not exist."""


@dataclass(frozen=True, slots=True)
class RunCreationResult:
    run: CrawlRun
    created: bool


def _find_run(session: Session, run_uid: str) -> CrawlRun | None:
    return session.scalar(select(CrawlRun).where(CrawlRun.run_uid == run_uid))


def _required_run(
    session: Session,
    run_uid: str,
    *,
    lock: bool = False,
) -> CrawlRun:
    query = select(CrawlRun).where(CrawlRun.run_uid == run_uid)
    if lock:
        query = query.with_for_update()
    run = session.scalar(query)
    if run is None:
        raise RunNotFound("crawler run was not found")
    return run


def create_run(
    session: Session,
    *,
    run_uid: str,
    scheduled_for: datetime,
    target_count: int,
    now: datetime,
) -> RunCreationResult:
    normalized_uid = run_uid.strip()
    if not normalized_uid:
        raise ValueError("crawler run UID must not be blank")
    if target_count <= 0:
        raise ValueError("crawler run target count must be positive")

    existing = _find_run(session, normalized_uid)
    if existing is not None:
        return RunCreationResult(run=existing, created=False)

    run = CrawlRun(
        run_uid=normalized_uid,
        status=RUNNING,
        scheduled_for=scheduled_for,
        started_at=now,
        target_count=target_count,
        leased_count=0,
        completed_count=0,
        failed_count=0,
        created_at=now,
        updated_at=now,
    )
    try:
        with session.begin_nested():
            session.add(run)
            session.flush()
    except IntegrityError:
        existing = _find_run(session, normalized_uid)
        if existing is not None:
            return RunCreationResult(run=existing, created=False)
        raise
    return RunCreationResult(run=run, created=True)


def request_run_stop(
    session: Session,
    *,
    run_uid: str,
    now: datetime,
) -> CrawlRun:
    run = _required_run(session, run_uid, lock=True)
    if run.status == STOP_REQUESTED:
        return run
    if run.status != RUNNING:
        raise RunStateError("only a running crawler run can request stop")
    run.status = STOP_REQUESTED
    run.stop_requested_at = now
    run.updated_at = now
    session.flush()
    return run


def finish_run(
    session: Session,
    *,
    run_uid: str,
    status: str,
    now: datetime,
) -> CrawlRun:
    if status not in TERMINAL_RUN_STATUSES:
        raise RunStateError("crawler run finish status must be terminal")
    run = _required_run(session, run_uid, lock=True)
    if run.status not in ACTIVE_RUN_STATUSES:
        raise RunStateError("crawler run is already terminal")
    run.status = status
    run.finished_at = now
    run.updated_at = now
    session.flush()
    return run


def get_active_run(session: Session) -> CrawlRun | None:
    return session.scalar(
        select(CrawlRun)
        .where(CrawlRun.status.in_(ACTIVE_RUN_STATUSES))
        .order_by(CrawlRun.scheduled_for.desc(), CrawlRun.id.desc())
        .limit(1)
    )
