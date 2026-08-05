"""Real SQLite infrastructure shared by crawler tests."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.crawler.db import CrawlerBase


NOW = datetime(2026, 7, 30, 1, 0, 0)


def make_sqlite_engine() -> Engine:
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _connection_record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    CrawlerBase.metadata.create_all(engine)
    return engine


@contextmanager
def sqlite_session() -> Iterator[Session]:
    engine = make_sqlite_engine()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        CrawlerBase.metadata.drop_all(engine)
        engine.dispose()
