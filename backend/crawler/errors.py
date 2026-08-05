"""Machine-readable Phase 2 crawler failures."""

from __future__ import annotations


class CrawlerError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.http_status = http_status


class Cancelled(CrawlerError):
    def __init__(self) -> None:
        super().__init__("cancelled", "crawler operation was cancelled")
