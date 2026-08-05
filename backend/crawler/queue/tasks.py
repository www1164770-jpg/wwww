"""Task queue operations shared by crawler worker types."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import random
from typing import Any
from urllib.parse import SplitResult, urlsplit, urlunsplit
from uuid import uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.crawler.db import CrawlRun, CrawlTask, utc_now
from backend.crawler.observability import (
    sanitize_error_code,
    sanitize_error_message,
)

from .states import (
    CANCELLED,
    COMPLETED,
    DEAD,
    FAILED,
    LEASED,
    PENDING,
    InvalidTaskTransition,
    assert_task_transition,
)


MAX_LEASE_BATCH = 100


@dataclass(frozen=True, slots=True)
class EnqueueResult:
    task: CrawlTask
    created: bool


@dataclass(frozen=True, slots=True)
class RecoveryResult:
    recovered_count: int
    dead_count: int


class TaskNotFound(LookupError):
    """Raised when a task UID is not present in the crawler database."""


class TaskLeaseOwnershipError(ValueError):
    """Raised when a worker does not own the task lease it is changing."""


def _normalized_http_target(parsed: SplitResult) -> str:
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("crawler task URL must not contain credentials")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("crawler task URL must contain a hostname")
    hostname = hostname.lower()
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("crawler task URL has an invalid port") from error
    default_port = 80 if parsed.scheme.lower() == "http" else 443
    netloc = hostname if port in (None, default_port) else f"{hostname}:{port}"
    return urlunsplit(
        (
            parsed.scheme.lower(),
            netloc,
            parsed.path or "/",
            parsed.query,
            "",
        )
    )


def normalize_task_target(target: str) -> str:
    value = target.strip()
    if not value:
        raise ValueError("crawler task target must not be blank")
    parsed = urlsplit(value)
    if parsed.scheme.lower() in {"http", "https"}:
        return _normalized_http_target(parsed)
    return value


def task_target_hash(normalized_target: str) -> str:
    return sha256(normalized_target.encode("utf-8")).hexdigest()


def _active_dedupe_key(material: str) -> str:
    return sha256(material.encode("utf-8")).hexdigest()


def _find_active_task(
    session: Session,
    *,
    task_type: str,
    active_dedupe_key: str,
) -> CrawlTask | None:
    return session.scalar(
        select(CrawlTask).where(
            CrawlTask.task_type == task_type,
            CrawlTask.active_dedupe_key == active_dedupe_key,
        )
    )


def enqueue_task(
    session: Session,
    *,
    task_type: str,
    target: str,
    payload: dict[str, Any] | None = None,
    priority: int = 100,
    run_id: int | None = None,
    available_at: datetime | None = None,
    dedupe_key: str | None = None,
) -> EnqueueResult:
    normalized_type = task_type.strip()
    if not normalized_type:
        raise ValueError("crawler task type must not be blank")
    normalized_target = normalize_task_target(target)
    if payload is not None and not isinstance(payload, dict):
        raise TypeError("crawler task payload must be a dictionary or None")
    if dedupe_key is not None and not dedupe_key.strip():
        raise ValueError("crawler task dedupe key must not be blank")

    dedupe_material = (
        dedupe_key.strip() if dedupe_key is not None else normalized_target
    )
    active_key = _active_dedupe_key(dedupe_material)
    existing = _find_active_task(
        session,
        task_type=normalized_type,
        active_dedupe_key=active_key,
    )
    if existing is not None:
        return EnqueueResult(task=existing, created=False)

    now = utc_now()
    task = CrawlTask(
        task_uid=uuid4().hex,
        run_id=run_id,
        task_type=normalized_type,
        target=normalized_target,
        target_hash=task_target_hash(normalized_target),
        dedupe_key=active_key,
        active_dedupe_key=active_key,
        payload_json=deepcopy(payload),
        priority=priority,
        status=PENDING,
        attempt_count=0,
        max_attempts=3,
        available_at=available_at or now,
        created_at=now,
        updated_at=now,
    )
    try:
        with session.begin_nested():
            session.add(task)
            session.flush()
    except IntegrityError:
        existing = _find_active_task(
            session,
            task_type=normalized_type,
            active_dedupe_key=active_key,
        )
        if existing is not None:
            return EnqueueResult(task=existing, created=False)
        raise
    return EnqueueResult(task=task, created=True)


def _validated_task_types(task_types: list[str]) -> tuple[str, ...]:
    normalized = tuple(task_type.strip() for task_type in task_types)
    if not normalized or any(not task_type for task_type in normalized):
        raise ValueError("at least one non-blank crawler task type is required")
    return normalized


def _validate_batch_limit(limit: int) -> None:
    if limit < 1 or limit > MAX_LEASE_BATCH:
        raise ValueError(
            f"crawler lease limit must be between 1 and {MAX_LEASE_BATCH}"
        )


def build_lease_query(
    *,
    task_types: list[str],
    now: datetime,
    limit: int,
):
    """Build the production row-lock query; SQLite ignores the lock clause."""

    from backend.crawler.scheduler.runs import RUNNING

    normalized_types = _validated_task_types(task_types)
    _validate_batch_limit(limit)
    running_run_exists = (
        select(CrawlRun.id)
        .where(
            CrawlRun.id == CrawlTask.run_id,
            CrawlRun.status == RUNNING,
        )
        .exists()
    )
    return (
        select(CrawlTask)
        .where(
            CrawlTask.status == PENDING,
            CrawlTask.available_at <= now,
            CrawlTask.task_type.in_(normalized_types),
            or_(CrawlTask.run_id.is_(None), running_run_exists),
        )
        .order_by(
            CrawlTask.priority.asc(),
            CrawlTask.available_at.asc(),
            CrawlTask.created_at.asc(),
            CrawlTask.id.asc(),
        )
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


def lease_tasks(
    session: Session,
    *,
    worker_id: str,
    task_types: list[str],
    limit: int,
    lease_seconds: int,
    now: datetime,
) -> list[CrawlTask]:
    normalized_worker_id = worker_id.strip()
    if not normalized_worker_id:
        raise ValueError("crawler worker ID must not be blank")
    if lease_seconds <= 0:
        raise ValueError("crawler lease duration must be positive")
    query = build_lease_query(task_types=task_types, now=now, limit=limit)
    tasks = list(session.scalars(query).all())
    leased_until = now + timedelta(seconds=lease_seconds)
    run_counts: dict[int, int] = {}

    for task in tasks:
        assert_task_transition(task.status, LEASED)
        task.status = LEASED
        task.worker_id = normalized_worker_id
        task.leased_at = now
        task.leased_until = leased_until
        task.updated_at = now
        if task.run_id is not None:
            run_counts[task.run_id] = run_counts.get(task.run_id, 0) + 1

    for run_id, count in run_counts.items():
        session.execute(
            update(CrawlRun)
            .where(CrawlRun.id == run_id)
            .values(
                leased_count=CrawlRun.leased_count + count,
                updated_at=now,
            ),
            execution_options={"synchronize_session": "fetch"},
        )
    session.flush()
    return tasks


def retry_delay_seconds(
    attempt_count: int,
    *,
    random_value: float | None = None,
) -> float:
    if attempt_count < 1:
        raise ValueError("crawler retry attempt must be positive")
    jitter_source = random.random() if random_value is None else random_value
    if not 0.0 <= jitter_source <= 1.0:
        raise ValueError("crawler retry jitter source must be between 0 and 1")
    base_delay = min(30 * (2 ** (attempt_count - 1)), 3600)
    return base_delay * (0.9 + (0.2 * jitter_source))


def _required_task(
    session: Session,
    task_uid: str,
    *,
    lock: bool = True,
) -> CrawlTask:
    query = select(CrawlTask).where(CrawlTask.task_uid == task_uid)
    if lock:
        query = query.with_for_update()
    task = session.scalar(query)
    if task is None:
        raise TaskNotFound("crawler task was not found")
    return task


def _assert_lease_owner(task: CrawlTask, worker_id: str) -> str:
    normalized_worker_id = worker_id.strip()
    if not normalized_worker_id:
        raise TaskLeaseOwnershipError("crawler worker ID must not be blank")
    if task.status != LEASED or task.worker_id != normalized_worker_id:
        raise TaskLeaseOwnershipError(
            "crawler task is not leased by the requesting worker"
        )
    return normalized_worker_id


def _clear_lease(task: CrawlTask, *, clear_worker: bool) -> None:
    task.leased_at = None
    task.leased_until = None
    if clear_worker:
        task.worker_id = None


def _increment_run_counter(
    session: Session,
    *,
    run_id: int | None,
    counter: str,
    now: datetime,
) -> None:
    if run_id is None:
        return
    if counter not in {"completed_count", "failed_count"}:
        raise ValueError("unsupported crawler run counter")
    column = getattr(CrawlRun, counter)
    session.execute(
        update(CrawlRun)
        .where(CrawlRun.id == run_id)
        .values(**{counter: column + 1, "updated_at": now}),
        execution_options={"synchronize_session": "fetch"},
    )


def complete_task(
    session: Session,
    *,
    task_uid: str,
    worker_id: str,
    now: datetime,
) -> CrawlTask:
    task = _required_task(session, task_uid)
    _assert_lease_owner(task, worker_id)
    assert_task_transition(task.status, COMPLETED)
    task.status = COMPLETED
    task.completed_at = now
    task.active_dedupe_key = None
    task.updated_at = now
    _clear_lease(task, clear_worker=False)
    _increment_run_counter(
        session,
        run_id=task.run_id,
        counter="completed_count",
        now=now,
    )
    session.flush()
    return task


def renew_task_lease(
    session: Session,
    *,
    task_uid: str,
    worker_id: str,
    lease_seconds: int,
    now: datetime,
) -> CrawlTask:
    if lease_seconds <= 0:
        raise ValueError("crawler lease duration must be positive")
    task = _required_task(session, task_uid)
    _assert_lease_owner(task, worker_id)
    task.leased_until = now + timedelta(seconds=lease_seconds)
    task.updated_at = now
    session.flush()
    return task


def cancel_leased_task(
    session: Session,
    *,
    task_uid: str,
    worker_id: str,
    now: datetime,
) -> CrawlTask:
    task = _required_task(session, task_uid)
    _assert_lease_owner(task, worker_id)
    assert_task_transition(task.status, CANCELLED)
    task.status = CANCELLED
    task.active_dedupe_key = None
    task.updated_at = now
    _clear_lease(task, clear_worker=True)
    session.flush()
    return task


def fail_task(
    session: Session,
    *,
    task_uid: str,
    worker_id: str,
    error_code: str,
    error_message: str,
    now: datetime,
    random_value: float | None = None,
    retryable: bool = True,
) -> CrawlTask:
    task = _required_task(session, task_uid)
    _assert_lease_owner(task, worker_id)
    assert_task_transition(task.status, FAILED)
    task.attempt_count += 1
    task.last_error_code = sanitize_error_code(error_code)
    task.last_error_message = sanitize_error_message(error_message)
    task.updated_at = now
    _clear_lease(task, clear_worker=True)

    if not retryable or task.attempt_count >= task.max_attempts:
        assert_task_transition(FAILED, DEAD)
        task.status = DEAD
        task.active_dedupe_key = None
        task.available_at = now
        _increment_run_counter(
            session,
            run_id=task.run_id,
            counter="failed_count",
            now=now,
        )
    else:
        task.status = FAILED
        task.available_at = now + timedelta(
            seconds=retry_delay_seconds(
                task.attempt_count,
                random_value=random_value,
            )
        )
    session.flush()
    return task


def retry_due_failed_tasks(
    session: Session,
    *,
    now: datetime,
    limit: int = MAX_LEASE_BATCH,
) -> int:
    _validate_batch_limit(limit)
    tasks = list(
        session.scalars(
            select(CrawlTask)
            .where(
                CrawlTask.status == FAILED,
                CrawlTask.available_at <= now,
            )
            .order_by(CrawlTask.available_at, CrawlTask.created_at, CrawlTask.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
    )
    for task in tasks:
        assert_task_transition(task.status, PENDING)
        task.status = PENDING
        task.updated_at = now
    session.flush()
    return len(tasks)


def cancel_task(
    session: Session,
    *,
    task_uid: str,
    now: datetime,
) -> CrawlTask:
    task = _required_task(session, task_uid)
    if task.status not in {PENDING, FAILED}:
        raise InvalidTaskTransition(
            "only pending or failed crawler tasks can be cancelled"
        )
    assert_task_transition(task.status, CANCELLED)
    task.status = CANCELLED
    task.active_dedupe_key = None
    task.updated_at = now
    _clear_lease(task, clear_worker=True)
    session.flush()
    return task


def recover_expired_leases(
    session: Session,
    *,
    now: datetime,
    random_value: float | None = None,
) -> RecoveryResult:
    tasks = list(
        session.scalars(
            select(CrawlTask)
            .where(
                CrawlTask.status == LEASED,
                CrawlTask.leased_until.is_not(None),
                CrawlTask.leased_until < now,
            )
            .order_by(CrawlTask.leased_until, CrawlTask.id)
            .limit(MAX_LEASE_BATCH)
            .with_for_update(skip_locked=True)
        ).all()
    )
    recovered_count = 0
    dead_count = 0
    for task in tasks:
        task.attempt_count += 1
        task.last_error_code = "lease_expired"
        task.last_error_message = "worker lease expired before completion"
        task.updated_at = now
        _clear_lease(task, clear_worker=True)
        if task.attempt_count >= task.max_attempts:
            assert_task_transition(LEASED, FAILED)
            assert_task_transition(FAILED, DEAD)
            task.status = DEAD
            task.active_dedupe_key = None
            task.available_at = now
            dead_count += 1
            _increment_run_counter(
                session,
                run_id=task.run_id,
                counter="failed_count",
                now=now,
            )
        else:
            assert_task_transition(LEASED, PENDING)
            task.status = PENDING
            task.available_at = now + timedelta(
                seconds=retry_delay_seconds(
                    task.attempt_count,
                    random_value=random_value,
                )
            )
            recovered_count += 1
    session.flush()
    return RecoveryResult(
        recovered_count=recovered_count,
        dead_count=dead_count,
    )
