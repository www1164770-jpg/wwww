"""Queue worker for versioned Phase 3 analysis and risk decisions."""

from __future__ import annotations

from dataclasses import dataclass
import os
import socket

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.crawler.config import CrawlerSettings
from backend.crawler.assets.persistence import enqueue_icon_task
from backend.crawler.db import CrawlTask, FetchResult, utc_now
from backend.crawler.queue.states import DEAD
from backend.crawler.queue.tasks import (
    complete_task,
    fail_task,
    lease_tasks,
    retry_due_failed_tasks,
)
from backend.crawler.risk import assess_risk
from backend.crawler.workers.heartbeats import heartbeat_worker, register_worker

from .contract import AnalysisSpec
from .persistence import (
    ANALYSIS_TASK_SCHEMA,
    CONTENT_ANALYSIS_TASK_TYPE,
    document_from_fetch,
    persist_analysis_result,
    persist_risk_decision,
)
from .service import analyze_document


@dataclass(frozen=True, slots=True)
class AnalysisWorkerOutcome:
    state: str
    task_uid: str | None = None
    analysis_uid: str | None = None
    decision_uid: str | None = None
    error_code: str | None = None


class AnalysisCrawlerWorker:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        settings: CrawlerSettings,
        model=None,
        worker_id: str | None = None,
        clock=utc_now,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.model = model
        self.worker_id = (worker_id or settings.worker_id).strip()
        self.clock = clock

    def _lease(self) -> CrawlTask | None:
        with self.session_factory.begin() as session:
            now = self.clock()
            register_worker(
                session,
                worker_id=self.worker_id,
                worker_type="analysis",
                process_id=os.getpid(),
                hostname=socket.gethostname(),
                now=now,
                metadata={"task_types": [CONTENT_ANALYSIS_TASK_TYPE, "analysis"]},
            )
            retry_due_failed_tasks(session, now=now)
            tasks = lease_tasks(
                session,
                worker_id=self.worker_id,
                task_types=[CONTENT_ANALYSIS_TASK_TYPE, "analysis"],
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
    def _fetch_uid(task: CrawlTask) -> tuple[str, str, AnalysisSpec]:
        payload = task.payload_json
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") not in {ANALYSIS_TASK_SCHEMA, "phase3-analysis-task-v1"}
            or not isinstance(payload.get("fetch_result_uid"), str)
            or not isinstance(payload.get("analysis_version"), str)
        ):
            raise ValueError("invalid analysis task payload")
        raw_spec = payload.get("analysis_spec") if isinstance(payload.get("analysis_spec"), dict) else {}
        return payload["fetch_result_uid"], payload["analysis_version"], AnalysisSpec(**{key: raw_spec.get(key, "") for key in AnalysisSpec.__dataclass_fields__})

    def process_one(self) -> AnalysisWorkerOutcome:
        task = self._lease()
        if task is None:
            return AnalysisWorkerOutcome("empty")
        try:
            fetch_uid, analysis_version, spec = self._fetch_uid(task)
            with self.session_factory() as session:
                fetch = session.scalar(
                    select(FetchResult).where(FetchResult.result_uid == fetch_uid)
                )
                if fetch is None:
                    raise ValueError("analysis source is unavailable")
                document = document_from_fetch(fetch)
            outcome = analyze_document(
                document,
                model=self.model,
                confidence_threshold=self.settings.analysis_confidence_threshold,
                rule_version=self.settings.analysis_rule_version,
                model_name=self.settings.ollama_model if self.model is not None else None,
            )
            assessment = assess_risk(
                document,
                outcome,
                rule_version=self.settings.risk_rule_version,
            )
            with self.session_factory.begin() as session:
                current = session.scalar(
                    select(CrawlTask).where(CrawlTask.task_uid == task.task_uid).with_for_update()
                )
                fetch = session.scalar(
                    select(FetchResult).where(FetchResult.result_uid == fetch_uid)
                )
                if current is None or fetch is None:
                    raise ValueError("analysis task state is unavailable")
                analysis = persist_analysis_result(
                    session,
                    fetch_result=fetch,
                    outcome=outcome,
                    analysis_version=analysis_version,
                    spec=spec,
                    task_uid=current.task_uid,
                    run_uid=(current.payload_json or {}).get("run_uid"),
                )
                decision = persist_risk_decision(
                    session,
                    analysis_result=analysis,
                    assessment=assessment,
                    decision_version=self.settings.risk_rule_version,
                )
                if self.settings.icon_fetch_enabled and decision.status != "rejected":
                    enqueue_icon_task(
                        session,
                        fetch_result=fetch,
                        source_url=fetch.apple_touch_icon_url or fetch.favicon_url,
                        run_id=current.run_id,
                        max_attempts=self.settings.max_attempts,
                        available_at=self.clock(),
                    )
                complete_task(
                    session,
                    task_uid=current.task_uid,
                    worker_id=self.worker_id,
                    now=self.clock(),
                )
                heartbeat_worker(session, worker_id=self.worker_id, now=self.clock())
                return AnalysisWorkerOutcome(
                    "completed",
                    current.task_uid,
                    analysis.analysis_uid,
                    decision.decision_uid,
                )
        except SQLAlchemyError:
            raise
        except (LookupError, TypeError, ValueError) as error:
            with self.session_factory.begin() as session:
                failed = fail_task(
                    session,
                    task_uid=task.task_uid,
                    worker_id=self.worker_id,
                    error_code="analysis_input_invalid",
                    error_message=str(error),
                    now=self.clock(),
                    retryable=False,
                )
            return AnalysisWorkerOutcome(
                "dead" if failed.status == DEAD else "retry_wait",
                task.task_uid,
                error_code="analysis_input_invalid",
            )


__all__ = ["AnalysisCrawlerWorker", "AnalysisWorkerOutcome"]
