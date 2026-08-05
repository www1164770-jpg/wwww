"""Central task states and legal transitions."""

from __future__ import annotations


PENDING = "pending"
LEASED = "leased"
COMPLETED = "completed"
FAILED = "failed"
DEAD = "dead"
CANCELLED = "cancelled"

TASK_STATUSES = frozenset(
    {
        PENDING,
        LEASED,
        COMPLETED,
        FAILED,
        DEAD,
        CANCELLED,
    }
)

LEGAL_TASK_TRANSITIONS = {
    PENDING: frozenset({LEASED, CANCELLED}),
    LEASED: frozenset({COMPLETED, FAILED, PENDING, CANCELLED}),
    FAILED: frozenset({PENDING, DEAD, CANCELLED}),
    COMPLETED: frozenset(),
    DEAD: frozenset(),
    CANCELLED: frozenset(),
}


class InvalidTaskTransition(ValueError):
    """Raised when a caller attempts to violate the task lifecycle."""


def assert_task_transition(current: str, target: str) -> None:
    if current not in TASK_STATUSES or target not in TASK_STATUSES:
        raise InvalidTaskTransition("unknown crawler task status")
    if target not in LEGAL_TASK_TRANSITIONS[current]:
        raise InvalidTaskTransition(
            f"crawler task transition {current} -> {target} is not allowed"
        )
