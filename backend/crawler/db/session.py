"""Explicit engine and transaction factories for the crawler database."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.crawler.config import CrawlerConfigError, CrawlerSettings


def create_crawler_engine(settings: CrawlerSettings) -> Engine:
    """Create an engine only after a crawler command requests one."""

    if not settings.database_url:
        raise CrawlerConfigError(
            "CRAWLER_DATABASE_URL is required before creating a crawler engine"
        )
    url = make_url(settings.database_url)
    if (
        url.get_backend_name() != "mysql"
        or (url.database or "") not in {"zhihui_crawler", "zhihui_crawler_test"}
    ):
        raise CrawlerConfigError(
            "crawler engine requires exactly zhihui_crawler or zhihui_crawler_test"
        )
    options: dict[str, object] = {"pool_pre_ping": True}
    if url.get_backend_name() == "mysql":
        options.update(
            {
                "pool_recycle": 300,
                "isolation_level": "READ COMMITTED",
            }
        )
    return create_engine(settings.database_url, **options)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()
