"""Safe one-shot command line interface for crawler infrastructure."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import datetime
import json
import os
import socket
import sys
import time
from typing import Any, TextIO
from uuid import uuid4

from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import SQLAlchemyError

from backend.crawler.config import CrawlerConfigError, CrawlerSettings
from backend.crawler.db import (
    AnalysisResult,
    CrawlRun,
    CrawlTask,
    DiscoveredLink,
    FetchResult,
    IconAsset,
    OutboxEvent,
    RiskDecision,
    ReviewCase,
    PublishRecord,
    WorkerHeartbeat,
    utc_now,
)
from backend.crawler.errors import CrawlerError
from backend.crawler.discovery.enqueue import enqueue_discovered_task
from backend.crawler.db.migration import (
    MigrationSafetyError,
    run_migrations,
    validate_migration_target,
)
from backend.crawler.db.session import (
    create_crawler_engine,
    create_session_factory,
    session_scope,
)
from backend.crawler.observability import configure_crawler_logging, log_event
from backend.crawler.queue.tasks import (
    enqueue_task,
    lease_tasks,
    recover_expired_leases,
)
from backend.crawler.net.url import normalize_http_url, safe_url_for_output
from backend.crawler.scheduler.runs import (
    RUNNING,
    STOP_REQUESTED,
    create_run,
    get_active_run,
    request_run_stop,
)
from backend.crawler.workers.heartbeats import (
    register_worker,
    worker_effective_status,
)
from backend.crawler.workers import StaticCrawlerWorker, build_static_handler
from backend.crawler.analysis.ollama import OllamaClient
from backend.crawler.analysis.worker import AnalysisCrawlerWorker
from backend.crawler.assets.factory import build_icon_downloader
from backend.crawler.assets.worker import IconCrawlerWorker
from backend.crawler.review.service import (
    approve_review, assign_review, create_review, reject_review,
)
from backend.crawler.review.preview import create_local_preview


COMMANDS = (
    "db-check",
    "migrate",
    "enqueue-smoke-task",
    "lease-smoke-task",
    "recover-expired",
    "worker-status",
    "run-create",
    "run-stop",
    "status",
    "enqueue-url",
    "fetch-once",
    "worker-once",
    "worker-run",
    "task-show",
    "result-show",
    "analysis-once",
    "analysis-run",
    "icon-once",
    "icon-run",
    "review-create",
    "review-list",
    "review-show",
    "review-assign",
    "review-approve",
    "review-reject",
    "publish-preview",
    "publish-enqueue",
    "publish-status",
    "publish-retry",
    "integration-readiness",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m backend.crawler.cli",
        description="Crawler infrastructure commands; no worker is started.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    descriptions = {
        "db-check": "Check the configured crawler database connection.",
        "migrate": "Apply safe forward-only crawler migrations.",
        "enqueue-smoke-task": "Enqueue one idempotent smoke task.",
        "lease-smoke-task": "Lease at most one smoke task.",
        "recover-expired": "Recover expired task leases.",
        "worker-status": "Show persisted worker heartbeat state.",
        "run-create": "Create a crawl run without starting workers.",
        "run-stop": "Request stop for the active crawl run.",
        "status": "Show crawler database status counts.",
        "enqueue-url": "Normalize and enqueue one static URL without fetching it.",
        "fetch-once": "Enqueue and process one static URL through the worker.",
        "worker-once": "Process at most one static crawler task.",
        "worker-run": "Process a bounded number of static crawler tasks.",
        "task-show": "Show one crawler task by UID.",
        "result-show": "Show one static fetch result by UID.",
        "analysis-once": "Process at most one Phase 3 analysis task.",
        "analysis-run": "Process a bounded number of Phase 3 analysis tasks.",
        "icon-once": "Process at most one Phase 3 icon task.",
        "icon-run": "Process a bounded number of Phase 3 icon tasks.",
        "review-create": "Create a pending human review from an analysis UID.",
        "review-list": "List crawler review cases.",
        "review-show": "Show one crawler review case.",
        "review-assign": "Assign a pending review to an administrator.",
        "review-approve": "Approve a reviewing case; never publishes it.",
        "review-reject": "Reject a pending or reviewing case.",
        "publish-preview": "Run crawler-side URL validation; never writes nav_site.",
        "publish-enqueue": "Require --confirm before any publish request.",
        "publish-status": "Show a publish record.",
        "publish-retry": "Report retry availability for a publish record.",
        "integration-readiness": "Read configuration readiness without connecting to a database.",
    }
    for command in COMMANDS:
        command_parser = subparsers.add_parser(
            command,
            help=descriptions[command],
        )
        command_parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Emit one machine-readable JSON object.",
        )
        if command in {"enqueue-url", "fetch-once"}:
            command_parser.add_argument("url")
        elif command == "task-show":
            command_parser.add_argument("task_uid")
        elif command == "result-show":
            command_parser.add_argument("result_uid")
        elif command in {"worker-run", "analysis-run", "icon-run"}:
            command_parser.add_argument("--max-jobs", type=int, default=20)
        elif command == "review-create":
            command_parser.add_argument("analysis_uid")
        elif command in {"review-show", "publish-enqueue"}:
            command_parser.add_argument("review_uid")
        elif command == "publish-preview":
            command_parser.add_argument("review_uid")
            command_parser.add_argument("--version", required=True, type=int)
        elif command in {"review-assign", "review-approve", "review-reject"}:
            command_parser.add_argument("review_uid")
            command_parser.add_argument("--version", required=True, type=int)
            if command == "review-assign":
                command_parser.add_argument("--reviewer", required=True)
        elif command in {"publish-status", "publish-retry"}:
            command_parser.add_argument("publish_uid")
        if command == "publish-enqueue":
            command_parser.add_argument("--confirm", action="store_true")
    return parser


def _iso(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds") if value is not None else None


def _run_data(run: CrawlRun | None) -> dict[str, Any] | None:
    if run is None:
        return None
    return {
        "run_uid": run.run_uid,
        "status": run.status,
        "scheduled_for": _iso(run.scheduled_for),
        "started_at": _iso(run.started_at),
        "stop_requested_at": _iso(run.stop_requested_at),
        "finished_at": _iso(run.finished_at),
        "target_count": run.target_count,
        "leased_count": run.leased_count,
        "completed_count": run.completed_count,
        "failed_count": run.failed_count,
    }


def _task_data(task: CrawlTask) -> dict[str, Any]:
    return {
        "task_uid": task.task_uid,
        "task_type": task.task_type,
        "status": task.status,
        "target": safe_url_for_output(task.target),
        "attempt_count": task.attempt_count,
        "leased_until": _iso(task.leased_until),
        "worker_id": task.worker_id,
    }


def _review_data(case: ReviewCase) -> dict[str, Any]:
    return {
        "review_uid": case.review_uid,
        "analysis_result_id": case.analysis_result_id,
        "fetch_result_id": case.fetch_result_id,
        "status": case.status,
        "priority": case.priority,
        "assigned_reviewer_id": case.assigned_reviewer_id,
        "selected_title": case.selected_title,
        "selected_url": safe_url_for_output(case.selected_url) if case.selected_url else None,
        "version": case.version,
    }


def _worker_data(
    worker: WorkerHeartbeat,
    *,
    now: datetime,
    stale_after_seconds: int,
) -> dict[str, Any]:
    return {
        "worker_id": worker.worker_id,
        "worker_type": worker.worker_type,
        "process_id": worker.process_id,
        "hostname": worker.hostname,
        "status": worker_effective_status(
            worker,
            now=now,
            stale_after_seconds=stale_after_seconds,
        ),
        "current_task_uid": worker.current_task_uid,
        "started_at": _iso(worker.started_at),
        "last_seen_at": _iso(worker.last_seen_at),
    }


def _grouped_counts(session, model) -> dict[str, int]:
    return {
        status: count
        for status, count in session.execute(
            select(model.status, func.count())
            .select_from(model)
            .group_by(model.status)
        ).all()
    }


def _execute_session_command(
    command: str,
    *,
    settings: CrawlerSettings,
    engine: Engine,
    arguments: argparse.Namespace,
) -> dict[str, Any]:
    now = utc_now()
    factory = create_session_factory(engine)

    if command in {"analysis-once", "analysis-run"}:
        limit = 1 if command == "analysis-once" else arguments.max_jobs
        if not 1 <= limit <= 1000:
            raise ValueError("max-jobs must be between 1 and 1000")
        worker = AnalysisCrawlerWorker(
            session_factory=factory,
            settings=settings,
            model=OllamaClient(
                endpoint=settings.ollama_endpoint,
                model=settings.ollama_model,
                timeout_seconds=settings.ollama_timeout_seconds,
            ),
        )
        outcomes = []
        for _index in range(limit):
            outcome = worker.process_one()
            outcomes.append(outcome)
            if outcome.state == "empty":
                break
        return {
            "processed_count": sum(item.state != "empty" for item in outcomes),
            "outcomes": [
                {
                    "state": item.state,
                    "task_uid": item.task_uid,
                    "analysis_uid": item.analysis_uid,
                    "decision_uid": item.decision_uid,
                    "error_code": item.error_code,
                }
                for item in outcomes
            ],
        }

    if command in {"icon-once", "icon-run"}:
        limit = 1 if command == "icon-once" else arguments.max_jobs
        if not 1 <= limit <= 1000:
            raise ValueError("max-jobs must be between 1 and 1000")
        downloader = build_icon_downloader(settings)
        try:
            worker = IconCrawlerWorker(
                session_factory=factory,
                settings=settings,
                downloader=downloader,
            )
            outcomes = []
            for _index in range(limit):
                outcome = worker.process_one()
                outcomes.append(outcome)
                if outcome.state == "empty":
                    break
            return {
                "processed_count": sum(item.state != "empty" for item in outcomes),
                "outcomes": [
                    {
                        "state": item.state,
                        "task_uid": item.task_uid,
                        "asset_uid": item.asset_uid,
                        "error_code": item.error_code,
                    }
                    for item in outcomes
                ],
            }
        finally:
            downloader.close()

    if command in {"worker-once", "worker-run"}:
        handler = build_static_handler(settings)
        worker = StaticCrawlerWorker(
            session_factory=factory,
            handler=handler,
            settings=settings,
        )
        if command == "worker-once":
            outcomes = (worker.process_one(),)
        else:
            outcomes = worker.run(max_jobs=arguments.max_jobs)
        return {
            "processed_count": sum(item.state != "empty" for item in outcomes),
            "outcomes": [
                {
                    "state": item.state,
                    "task_uid": item.task_uid,
                    "result_uid": item.result_uid,
                    "error_code": item.error_code,
                }
                for item in outcomes
            ],
        }

    if command == "fetch-once":
        normalized = normalize_http_url(arguments.url)
        with session_scope(factory) as session:
            active_run = get_active_run(session)
            result = enqueue_discovered_task(
                session,
                task_type="static_fetch",
                target=normalized.url,
                payload={
                    "target_url": normalized.url,
                    "normalized_url": normalized.url,
                    "depth": 0,
                    "parent_url": None,
                    "run_uid": active_run.run_uid if active_run else f"fetch-{uuid4().hex}",
                    "max_depth": settings.max_depth,
                    "max_pages": settings.max_pages_per_origin,
                    "discovery_policy": "same_origin",
                },
                run_id=active_run.id if active_run else None,
                priority=-1_000_000,
            )
            result.task.max_attempts = settings.max_attempts
            task_uid = result.task.task_uid
        worker = StaticCrawlerWorker(
            session_factory=factory,
            handler=build_static_handler(settings),
            settings=settings,
        )
        outcome = worker.process_one()
        if outcome.task_uid != task_uid or outcome.state != "completed":
            raise CrawlerError(outcome.error_code or "fetch_failed", "static fetch did not complete")
        return {
            "task_uid": task_uid,
            "result_uid": outcome.result_uid,
            "state": outcome.state,
        }

    with session_scope(factory) as session:
        if command == "review-create":
            analysis = session.scalar(select(AnalysisResult).where(
                AnalysisResult.analysis_uid == arguments.analysis_uid
            ))
            if analysis is None:
                raise LookupError("analysis result was not found")
            case = create_review(
                session,
                fetch_result_id=analysis.fetch_result_id,
                analysis_result_id=analysis.id,
                actor_id="cli",
            )
            return _review_data(case)

        if command == "review-list":
            cases = list(session.scalars(select(ReviewCase).order_by(
                ReviewCase.priority, ReviewCase.created_at
            )).all())
            return {"reviews": [_review_data(case) for case in cases]}

        if command in {"review-show", "review-assign", "review-approve", "review-reject", "publish-preview", "publish-enqueue"}:
            case = session.scalar(select(ReviewCase).where(
                ReviewCase.review_uid == arguments.review_uid
            ))
            if case is None:
                raise LookupError("review case was not found")
            if command == "review-show":
                return _review_data(case)
            if command == "review-assign":
                return _review_data(assign_review(
                    session, case, reviewer_id=arguments.reviewer,
                    expected_version=arguments.version, actor_id="cli",
                ))
            if command == "review-approve":
                return _review_data(approve_review(
                    session, case, expected_version=arguments.version, actor_id="cli",
                ))
            if command == "review-reject":
                return _review_data(reject_review(
                    session, case, expected_version=arguments.version, actor_id="cli",
                ))
            if command == "publish-preview":
                case, preview = create_local_preview(
                    session, case, expected_version=arguments.version, actor_id="cli",
                    ttl_seconds=settings.publish_preview_ttl_seconds,
                )
                return {"review": _review_data(case), "preview_uid": preview.preview_uid,
                        "preview": preview.result_json, "review_version": preview.review_version,
                        "content_hash": preview.content_hash, "nav_site_sync": "unconfigured"}
            if not arguments.confirm:
                raise ValueError("publish-enqueue requires --confirm")
            return {"review": _review_data(case), "state": "nav_site_sync_unconfigured"}

        if command in {"publish-status", "publish-retry"}:
            record = session.scalar(select(PublishRecord).where(
                PublishRecord.publish_uid == arguments.publish_uid
            ))
            if record is None:
                raise LookupError("publish record was not found")
            return {"publish_uid": record.publish_uid, "status": record.status,
                    "attempt_count": record.attempt_count,
                    "retry": "use the explicit review publish endpoint" if command == "publish-retry" else None}

        if command == "enqueue-url":
            normalized = normalize_http_url(arguments.url)
            active_run = get_active_run(session)
            result = enqueue_discovered_task(
                session,
                task_type="static_fetch",
                target=normalized.url,
                payload={
                    "target_url": normalized.url,
                    "normalized_url": normalized.url,
                    "depth": 0,
                    "parent_url": None,
                    "run_uid": active_run.run_uid if active_run else f"seed-{normalized.fingerprint[:20]}",
                    "max_depth": settings.max_depth,
                    "max_pages": settings.max_pages_per_origin,
                    "discovery_policy": "same_origin",
                },
                run_id=active_run.id if active_run else None,
            )
            if result.created:
                result.task.max_attempts = settings.max_attempts
            return {
                "created": result.created,
                "task_uid": result.task.task_uid,
                "status": result.task.status,
                "normalized_url": safe_url_for_output(normalized.url),
            }

        if command == "task-show":
            task = session.scalar(
                select(CrawlTask).where(CrawlTask.task_uid == arguments.task_uid)
            )
            if task is None:
                raise LookupError("crawler task was not found")
            return _task_data(task)

        if command == "result-show":
            result = session.scalar(
                select(FetchResult).where(FetchResult.result_uid == arguments.result_uid)
            )
            if result is None:
                raise LookupError("crawler fetch result was not found")
            return {
                "result_uid": result.result_uid,
                "task_id": result.task_id,
                "status": result.status,
                "requested_url": safe_url_for_output(result.requested_url),
                "final_url": safe_url_for_output(result.final_url) if result.final_url else None,
                "http_status": result.http_status,
                "content_type": result.content_type,
                "bytes_read": result.bytes_read,
                "title": result.title,
                "language": result.language,
                "content_hash": result.content_hash,
                "fetched_at": _iso(result.fetched_at),
                "error_code": result.error_code,
            }

        if command == "enqueue-smoke-task":
            active_run = get_active_run(session)
            run_id = (
                active_run.id
                if active_run is not None and active_run.status == RUNNING
                else None
            )
            result = enqueue_task(
                session,
                task_type="smoke",
                target="https://example.com/",
                payload={"source": "crawler_cli_smoke"},
                run_id=run_id,
                available_at=now,
            )
            if result.created:
                result.task.max_attempts = settings.max_attempts
            return {
                "created": result.created,
                "task_uid": result.task.task_uid,
                "status": result.task.status,
                "run_uid": active_run.run_uid if run_id is not None else None,
            }

        if command == "lease-smoke-task":
            register_worker(
                session,
                worker_id=settings.worker_id,
                worker_type="cli_smoke",
                process_id=os.getpid(),
                hostname=socket.gethostname(),
                now=now,
                metadata={"runtime": "python"},
            )
            tasks = lease_tasks(
                session,
                worker_id=settings.worker_id,
                task_types=["smoke"],
                limit=1,
                lease_seconds=settings.lease_seconds,
                now=now,
            )
            return {
                "state": "leased" if tasks else "empty",
                "task": _task_data(tasks[0]) if tasks else None,
            }

        if command == "recover-expired":
            result = recover_expired_leases(session, now=now)
            return {
                "recovered_count": result.recovered_count,
                "dead_count": result.dead_count,
            }

        if command == "worker-status":
            stale_after = max(settings.lease_seconds * 2, 60)
            workers = list(
                session.scalars(
                    select(WorkerHeartbeat).order_by(
                        WorkerHeartbeat.worker_id
                    )
                ).all()
            )
            return {
                "workers": [
                    _worker_data(
                        worker,
                        now=now,
                        stale_after_seconds=stale_after,
                    )
                    for worker in workers
                ]
            }

        if command == "run-create":
            run_uid = (
                f"night-{now:%Y%m%dT%H%M%S}-{uuid4().hex[:8]}"
            )
            result = create_run(
                session,
                run_uid=run_uid,
                scheduled_for=now,
                target_count=settings.nightly_target,
                now=now,
            )
            return {
                "created": result.created,
                **(_run_data(result.run) or {}),
            }

        if command == "run-stop":
            active_run = get_active_run(session)
            if active_run is None:
                return {"stop_requested": False, "run_uid": None}
            stopped = (
                active_run
                if active_run.status == STOP_REQUESTED
                else request_run_stop(
                    session,
                    run_uid=active_run.run_uid,
                    now=now,
                )
            )
            return {
                "stop_requested": True,
                "run_uid": stopped.run_uid,
                "status": stopped.status,
            }

        if command == "status":
            active_run = get_active_run(session)
            stale_after = max(settings.lease_seconds * 2, 60)
            workers = list(session.scalars(select(WorkerHeartbeat)).all())
            worker_counts: dict[str, int] = {}
            for worker in workers:
                status = worker_effective_status(
                    worker,
                    now=now,
                    stale_after_seconds=stale_after,
                )
                worker_counts[status] = worker_counts.get(status, 0) + 1
            return {
                "active_run": _run_data(active_run),
                "tasks": _grouped_counts(session, CrawlTask),
                "outbox": _grouped_counts(session, OutboxEvent),
                "workers": worker_counts,
                "fetch_results": session.scalar(select(func.count()).select_from(FetchResult)),
                "discovered_links": session.scalar(select(func.count()).select_from(DiscoveredLink)),
                "analysis_results": session.scalar(select(func.count()).select_from(AnalysisResult)),
                "risk_decisions": session.scalar(select(func.count()).select_from(RiskDecision)),
                "icon_assets": session.scalar(select(func.count()).select_from(IconAsset)),
            }

    raise ValueError("unknown crawler command")


def _execute_command(
    command: str,
    *,
    settings: CrawlerSettings,
    engine: Engine,
    arguments: argparse.Namespace,
) -> dict[str, Any]:
    if command == "db-check":
        with engine.connect() as connection:
            value = connection.execute(text("SELECT 1")).scalar_one()
        if value != 1:
            raise SQLAlchemyError("crawler database check failed")
        return {"database": "ok"}
    if command == "migrate":
        if settings.database_url is None:
            raise CrawlerConfigError("CRAWLER_DATABASE_URL is required")
        result = run_migrations(engine, settings.database_url)
        return {
            "database": result.database_name,
            "applied_versions": list(result.applied_versions),
            "skipped_versions": list(result.skipped_versions),
        }
    return _execute_session_command(
        command,
        settings=settings,
        engine=engine,
        arguments=arguments,
    )


def _success_payload(command: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "command": command, "data": data}


def integration_readiness(environ: Mapping[str, str]) -> dict[str, bool]:
    """Only report presence/contract readiness; never reveal or use URL values."""
    configured = lambda name: bool(environ.get(name, "").strip())
    nav_sync = environ.get("CRAWLER_NAV_SITE_SYNC_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
    crawler_db = configured("CRAWLER_DATABASE_URL")
    test_db = configured("CRAWLER_TEST_DATABASE_URL")
    target_db = configured("CRAWLER_NAV_SITE_DATABASE_URL")
    allowed_db = configured("CRAWLER_NAV_SITE_ALLOWED_DATABASE")
    return {
        "crawler_database_configured": crawler_db,
        "crawler_test_database_configured": test_db,
        "nav_sync_enabled": nav_sync,
        "nav_target_database_configured": target_db,
        "nav_allowed_database_configured": allowed_db,
        "analysis_contract_ready": True,
        "review_contract_ready": True,
        "publish_adapter_ready": False,
        "mysql_integration_ready": crawler_db and test_db,
        "publish_e2e_ready": False,
    }


def _error_payload(
    command: str,
    *,
    code: str,
    message: str,
) -> dict[str, Any]:
    return {
        "ok": False,
        "command": command,
        "error": {"code": code, "message": message},
    }


def _emit(
    payload: dict[str, Any],
    *,
    json_output: bool,
    stream: TextIO,
) -> None:
    if json_output:
        print(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            file=stream,
        )
        return
    if payload["ok"]:
        print(f"{payload['command']}: ok", file=stream)
    else:
        print(
            f"{payload['command']}: {payload['error']['message']}",
            file=stream,
        )


def _close_logger(logger) -> None:
    if logger is None:
        return
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    output = stdout or sys.stdout
    error_output = stderr or sys.stderr
    arguments = build_parser().parse_args(argv)
    command = arguments.command
    json_output = arguments.json_output
    engine: Engine | None = None
    logger = None
    started = time.monotonic()
    try:
        if command == "integration-readiness":
            values = os.environ if environ is None else environ
            data = integration_readiness(values)
            _emit(_success_payload(command, data), json_output=json_output, stream=output)
            return 0 if data["mysql_integration_ready"] and data["publish_e2e_ready"] else (2 if not data["crawler_database_configured"] else 6)
        settings = CrawlerSettings.from_env(
            environ,
            require_database=True,
        )
        if command == "migrate" and settings.database_url is not None:
            validate_migration_target(settings.database_url)
        logger = configure_crawler_logging(settings, component="cli")
        engine = create_crawler_engine(settings)
        data = _execute_command(
            command,
            settings=settings,
            engine=engine,
            arguments=arguments,
        )
        duration_ms = round((time.monotonic() - started) * 1000)
        log_event(
            logger,
            "command_completed",
            duration_ms=duration_ms,
            command=command,
        )
        _emit(
            _success_payload(command, data),
            json_output=json_output,
            stream=output,
        )
        return 0
    except CrawlerConfigError:
        payload = _error_payload(
            command,
            code="configuration_error",
            message="CRAWLER_DATABASE_URL is required for crawler commands",
        )
        _emit(payload, json_output=json_output, stream=error_output)
        return 2
    except MigrationSafetyError:
        payload = _error_payload(
            command,
            code="migration_refused",
            message="crawler migration target was refused by the safety policy",
        )
        _emit(payload, json_output=json_output, stream=error_output)
        return 4
    except SQLAlchemyError:
        if logger is not None:
            log_event(
                logger,
                "command_failed",
                error_code="database_unavailable",
                command=command,
            )
        payload = _error_payload(
            command,
            code="database_unavailable",
            message="crawler database is unavailable",
        )
        _emit(payload, json_output=json_output, stream=error_output)
        return 3
    except CrawlerError as caught:
        if logger is not None:
            log_event(
                logger,
                "command_failed",
                error_code=caught.code,
                command=command,
            )
        payload = _error_payload(
            command,
            code="fetch_error",
            message="crawler fetch did not complete",
        )
        _emit(payload, json_output=json_output, stream=error_output)
        return 5
    except (LookupError, ValueError, TypeError):
        if logger is not None:
            log_event(
                logger,
                "command_failed",
                error_code="command_rejected",
                command=command,
            )
        payload = _error_payload(
            command,
            code="command_rejected",
            message="crawler command was rejected",
        )
        _emit(payload, json_output=json_output, stream=error_output)
        return 4
    except Exception:
        if logger is not None:
            log_event(
                logger,
                "command_failed",
                error_code="internal_error",
                command=command,
            )
        payload = _error_payload(
            command,
            code="internal_error",
            message="crawler command failed",
        )
        _emit(payload, json_output=json_output, stream=error_output)
        return 5
    finally:
        if engine is not None:
            engine.dispose()
        _close_logger(logger)


__all__ = ["build_parser", "main"]
