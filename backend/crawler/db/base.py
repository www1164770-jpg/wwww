"""SQLAlchemy primitives owned exclusively by the crawler database."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import DeclarativeBase


BIGINT_ID = BigInteger().with_variant(Integer, "sqlite")


def utc_now() -> datetime:
    """Return a UTC value stored as a timezone-naive database timestamp."""

    return datetime.now(UTC).replace(tzinfo=None)


class CrawlerBase(DeclarativeBase):
    """Metadata boundary for the independent zhihui_crawler database."""
