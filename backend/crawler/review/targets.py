"""Publish-target boundary; disabled unless a separately audited adapter is supplied.

This module intentionally contains no application-model import and no database
connection code.  A deployment must provide a target adapter only after the
target has been verified as an explicitly allowed isolated database.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.crawler.review.mapping import WebsiteFields
from backend.crawler.review.publish import PublishUnavailable


@dataclass(frozen=True, slots=True)
class PublishCommand:
    idempotency_key: str
    fields: WebsiteFields


@dataclass(frozen=True, slots=True)
class TargetPublishOutcome:
    target_record_id: int
    idempotency_key: str


class PublishTarget(Protocol):
    def validate_configuration(self) -> None: ...
    def publish(self, command: PublishCommand) -> TargetPublishOutcome: ...
    def find_by_idempotency_key(self, idempotency_key: str) -> TargetPublishOutcome | None: ...


class DisabledPublishTarget:
    """Safe default used for all crawler deployments."""

    def validate_configuration(self) -> None:
        raise PublishUnavailable("publish_target_unavailable")

    def publish(self, command: PublishCommand) -> TargetPublishOutcome:
        raise PublishUnavailable("publish target adapter is not configured")

    def find_by_idempotency_key(self, idempotency_key: str) -> TargetPublishOutcome | None:
        raise PublishUnavailable("publish target adapter is not configured")


class InMemoryPublishTarget:
    """Test-only target that models idempotency and recoverable lost responses."""

    def __init__(self, *, fail_before_write: bool = False, lose_response_after_write: bool = False, permanent_failure: bool = False) -> None:
        self.fail_before_write = fail_before_write
        self.lose_response_after_write = lose_response_after_write
        self.permanent_failure = permanent_failure
        self.calls = 0
        self.records: dict[str, TargetPublishOutcome] = {}

    def validate_configuration(self) -> None:
        return None

    def publish(self, command: PublishCommand) -> TargetPublishOutcome:
        self.calls += 1
        if self.permanent_failure:
            raise ValueError("target_permanent_failure")
        if self.fail_before_write:
            raise TimeoutError("target_retryable_failure")
        existing = self.records.get(command.idempotency_key)
        if existing is not None:
            return existing
        outcome = TargetPublishOutcome(len(self.records) + 1, command.idempotency_key)
        self.records[command.idempotency_key] = outcome
        if self.lose_response_after_write:
            self.lose_response_after_write = False
            raise TimeoutError("target_response_lost")
        return outcome

    def find_by_idempotency_key(self, idempotency_key: str) -> TargetPublishOutcome | None:
        return self.records.get(idempotency_key)
