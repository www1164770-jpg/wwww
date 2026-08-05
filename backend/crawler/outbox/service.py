"""Transactional outbox primitives without a production sync adapter."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.crawler.db import OutboxEvent, utc_now
from backend.crawler.observability import sanitize_error_message
from backend.crawler.queue.tasks import retry_delay_seconds


PENDING = "pending"
LEASED = "leased"
PROCESSED = "processed"
DEAD = "dead"
MAX_OUTBOX_BATCH = 100


class OutboxNotFound(LookupError):
    """Raised when an outbox event UID does not exist."""


class OutboxLeaseOwnershipError(ValueError):
    """Raised when a worker does not own an outbox event lease."""


@dataclass(frozen=True, slots=True)
class OutboxEnqueueResult:
    event: OutboxEvent
    created: bool


def _find_event(
    session: Session,
    event_uid: str,
    *,
    lock: bool = False,
) -> OutboxEvent | None:
    query = select(OutboxEvent).where(OutboxEvent.event_uid == event_uid)
    if lock:
        query = query.with_for_update()
    return session.scalar(query)


def _required_event(session: Session, event_uid: str) -> OutboxEvent:
    event = _find_event(session, event_uid, lock=True)
    if event is None:
        raise OutboxNotFound("crawler outbox event was not found")
    return event


def _non_blank(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} must not be blank")
    return normalized


def enqueue_outbox_event(
    session: Session,
    *,
    event_uid: str,
    aggregate_type: str,
    aggregate_uid: str,
    event_type: str,
    payload: dict[str, Any],
    available_at: datetime | None = None,
) -> OutboxEnqueueResult:
    normalized_uid = _non_blank("crawler outbox event UID", event_uid)
    normalized_aggregate_type = _non_blank(
        "crawler outbox aggregate type",
        aggregate_type,
    )
    normalized_aggregate_uid = _non_blank(
        "crawler outbox aggregate UID",
        aggregate_uid,
    )
    normalized_event_type = _non_blank(
        "crawler outbox event type",
        event_type,
    )
    if not isinstance(payload, dict):
        raise TypeError("crawler outbox payload must be a dictionary")

    existing = _find_event(session, normalized_uid)
    if existing is not None:
        return OutboxEnqueueResult(event=existing, created=False)

    now = utc_now()
    event = OutboxEvent(
        event_uid=normalized_uid,
        aggregate_type=normalized_aggregate_type,
        aggregate_uid=normalized_aggregate_uid,
        event_type=normalized_event_type,
        payload_json=deepcopy(payload),
        status=PENDING,
        attempt_count=0,
        max_attempts=3,
        available_at=available_at or now,
        created_at=now,
        updated_at=now,
    )
    try:
        with session.begin_nested():
            session.add(event)
            session.flush()
    except IntegrityError:
        existing = _find_event(session, normalized_uid)
        if existing is not None:
            return OutboxEnqueueResult(event=existing, created=False)
        raise
    return OutboxEnqueueResult(event=event, created=True)


def _validate_lease_inputs(
    *,
    worker_id: str,
    limit: int,
    lease_seconds: int,
) -> str:
    normalized_worker_id = worker_id.strip()
    if not normalized_worker_id:
        raise ValueError("crawler outbox worker ID must not be blank")
    if limit < 1 or limit > MAX_OUTBOX_BATCH:
        raise ValueError(
            f"crawler outbox limit must be between 1 and {MAX_OUTBOX_BATCH}"
        )
    if lease_seconds <= 0:
        raise ValueError("crawler outbox lease duration must be positive")
    return normalized_worker_id


def build_outbox_lease_query(*, now: datetime, limit: int):
    if limit < 1 or limit > MAX_OUTBOX_BATCH:
        raise ValueError(
            f"crawler outbox limit must be between 1 and {MAX_OUTBOX_BATCH}"
        )
    return (
        select(OutboxEvent)
        .where(
            OutboxEvent.status == PENDING,
            OutboxEvent.available_at <= now,
        )
        .order_by(
            OutboxEvent.available_at,
            OutboxEvent.created_at,
            OutboxEvent.id,
        )
        .limit(limit)
        .with_for_update(skip_locked=True)
    )


def lease_outbox_events(
    session: Session,
    *,
    worker_id: str,
    limit: int,
    lease_seconds: int,
    now: datetime,
) -> list[OutboxEvent]:
    normalized_worker_id = _validate_lease_inputs(
        worker_id=worker_id,
        limit=limit,
        lease_seconds=lease_seconds,
    )
    events = list(
        session.scalars(
            build_outbox_lease_query(now=now, limit=limit)
        ).all()
    )
    leased_until = now + timedelta(seconds=lease_seconds)
    for event in events:
        event.status = LEASED
        event.worker_id = normalized_worker_id
        event.leased_at = now
        event.leased_until = leased_until
        event.updated_at = now
    session.flush()
    return events


def _assert_owner(event: OutboxEvent, worker_id: str) -> None:
    if event.status != LEASED or event.worker_id != worker_id.strip():
        raise OutboxLeaseOwnershipError(
            "crawler outbox event is not leased by the requesting worker"
        )


def mark_outbox_processed(
    session: Session,
    *,
    event_uid: str,
    worker_id: str,
    now: datetime,
) -> OutboxEvent:
    event = _required_event(session, event_uid)
    _assert_owner(event, worker_id)
    event.status = PROCESSED
    event.processed_at = now
    event.leased_at = None
    event.leased_until = None
    event.updated_at = now
    session.flush()
    return event


def fail_outbox_event(
    session: Session,
    *,
    event_uid: str,
    worker_id: str,
    error_message: str,
    now: datetime,
    random_value: float | None = None,
) -> OutboxEvent:
    event = _required_event(session, event_uid)
    _assert_owner(event, worker_id)
    event.attempt_count += 1
    event.last_error = sanitize_error_message(error_message)
    event.worker_id = None
    event.leased_at = None
    event.leased_until = None
    event.updated_at = now
    if event.attempt_count >= event.max_attempts:
        event.status = DEAD
        event.available_at = now
    else:
        event.status = PENDING
        event.available_at = now + timedelta(
            seconds=retry_delay_seconds(
                event.attempt_count,
                random_value=random_value,
            )
        )
    session.flush()
    return event
