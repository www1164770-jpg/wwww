"""Queue worker for SSRF-checked Phase 3 icon assets."""

from __future__ import annotations

from dataclasses import dataclass
import os
import socket

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.crawler.config import CrawlerSettings
from backend.crawler.db import CrawlTask, FetchResult, utc_now
from backend.crawler.errors import CrawlerError
from backend.crawler.queue.states import DEAD
from backend.crawler.queue.tasks import complete_task, fail_task, lease_tasks, retry_due_failed_tasks
from backend.crawler.workers.heartbeats import heartbeat_worker, register_worker

from .icons import IconValidationError
from .persistence import ICON_TASK_SCHEMA, persist_icon_asset


@dataclass(frozen=True, slots=True)
class IconWorkerOutcome:
    state: str
    task_uid: str | None = None
    asset_uid: str | None = None
    error_code: str | None = None


class IconCrawlerWorker:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        settings: CrawlerSettings,
        downloader,
        worker_id: str | None = None,
        clock=utc_now,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.downloader = downloader
        self.worker_id = (worker_id or settings.worker_id).strip()
        self.clock = clock

    def _lease(self) -> CrawlTask | None:
        with self.session_factory.begin() as session:
            now = self.clock()
            register_worker(
                session,
                worker_id=self.worker_id,
                worker_type="icon",
                process_id=os.getpid(),
                hostname=socket.gethostname(),
                now=now,
                metadata={"task_types": ["icon_fetch"]},
            )
            retry_due_failed_tasks(session, now=now)
            tasks = lease_tasks(
                session,
                worker_id=self.worker_id,
                task_types=["icon_fetch"],
                limit=1,
                lease_seconds=self.settings.lease_seconds,
                now=now,
            )
            if not tasks:
                return None
            heartbeat_worker(
                session,
                worker_id=self.worker_id,
                now=now,
                current_task_uid=tasks[0].task_uid,
            )
            return tasks[0]

    @staticmethod
    def _fetch_uid(task: CrawlTask) -> str:
        payload = task.payload_json
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != ICON_TASK_SCHEMA
            or not isinstance(payload.get("fetch_result_uid"), str)
        ):
            raise ValueError("invalid icon task payload")
        return payload["fetch_result_uid"]

    def process_one(self) -> IconWorkerOutcome:
        task = self._lease()
        if task is None:
            return IconWorkerOutcome("empty")
        try:
            fetch_uid = self._fetch_uid(task)
            stored = self.downloader.download(task.target, root=self.settings.icon_root)
            with self.session_factory.begin() as session:
                current = session.scalar(
                    select(CrawlTask).where(CrawlTask.task_uid == task.task_uid).with_for_update()
                )
                fetch = session.scalar(
                    select(FetchResult).where(FetchResult.result_uid == fetch_uid)
                )
                if current is None or fetch is None:
                    raise ValueError("icon task state is unavailable")
                asset = persist_icon_asset(
                    session,
                    fetch_result=fetch,
                    stored=stored,
                    fetched_at=self.clock(),
                )
                complete_task(
                    session,
                    task_uid=current.task_uid,
                    worker_id=self.worker_id,
                    now=self.clock(),
                )
                heartbeat_worker(session, worker_id=self.worker_id, now=self.clock())
                return IconWorkerOutcome("completed", current.task_uid, asset.asset_uid)
        except SQLAlchemyError:
            raise
        except (CrawlerError, IconValidationError, LookupError, TypeError, ValueError) as error:
            error_code = getattr(error, "code", "icon_input_invalid")
            retryable = bool(getattr(error, "retryable", False))
            with self.session_factory.begin() as session:
                failed = fail_task(
                    session,
                    task_uid=task.task_uid,
                    worker_id=self.worker_id,
                    error_code=error_code,
                    error_message=str(error),
                    now=self.clock(),
                    retryable=retryable,
                )
            return IconWorkerOutcome(
                "dead" if failed.status == DEAD else "retry_wait",
                task.task_uid,
                error_code=error_code,
            )


__all__ = ["IconCrawlerWorker", "IconWorkerOutcome"]
