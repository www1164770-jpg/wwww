"""The explicit, human-driven review state machine."""

from __future__ import annotations

PENDING = "pending"
REVIEWING = "reviewing"
APPROVED = "approved"
REJECTED = "rejected"
PUBLISH_READY = "publish_ready"
PUBLISHING = "publishing"
PUBLISH_FAILED = "publish_failed"
PUBLISHED = "published"
ASSIGNED = REVIEWING
SUBMITTED = REVIEWING

REVIEW_STATUSES = frozenset({PENDING, REVIEWING, APPROVED, REJECTED, PUBLISH_READY, PUBLISHING, PUBLISH_FAILED, PUBLISHED})
LEGAL_REVIEW_TRANSITIONS = {
    PENDING: {REVIEWING, REJECTED},
    REVIEWING: {APPROVED, REJECTED},
    APPROVED: {PUBLISH_READY},
    REJECTED: set(),
    PUBLISH_READY: {PUBLISHING},
    PUBLISHING: {PUBLISHED, PUBLISH_FAILED},
    PUBLISH_FAILED: {PUBLISHING},
    PUBLISHED: set(),
}


class InvalidReviewTransition(ValueError):
    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(f"invalid review transition: {current} -> {target}")


def assert_review_transition(current: str, target: str) -> None:
    if target not in LEGAL_REVIEW_TRANSITIONS.get(current, set()):
        raise InvalidReviewTransition(current, target)
