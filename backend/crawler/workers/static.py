"""Phase 2 static-fetch handler and worker runtime built on the Phase 1 queue."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
import os
import socket
import threading
from urllib.parse import urljoin

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.crawler.config import CrawlerSettings
from backend.crawler.analysis.contract import AnalysisSpec
from backend.crawler.analysis.persistence import enqueue_analysis_task
from backend.crawler.db import CrawlRun, CrawlTask, FetchResult, utc_now
from backend.crawler.discovery.feed import FeedDocument, parse_feed
from backend.crawler.discovery.enqueue import enqueue_discovered_task
from backend.crawler.discovery.html import HtmlDocument, HtmlLink, parse_html
from backend.crawler.discovery.links import (
    DiscoveredCandidate,
    DiscoveryPolicy,
    select_discovered_links,
)
from backend.crawler.discovery.sitemap import SitemapDocument, SitemapError, parse_sitemap
from backend.crawler.errors import Cancelled, CrawlerError
from backend.crawler.fetch.http import HttpFetchResult, StaticHttpFetcher
from backend.crawler.fetch.persistence import (
    persist_discovered_links,
    persist_fetch_failure,
    persist_fetch_result,
)
from backend.crawler.net.url import InvalidUrl, normalize_http_url, same_origin
from backend.crawler.queue.states import DEAD
from backend.crawler.scheduler.runs import STOP_REQUESTED
from backend.crawler.queue.tasks import (
    cancel_leased_task,
    complete_task,
    enqueue_task,
    fail_task,
    lease_tasks,
    renew_task_lease,
    retry_due_failed_tasks,
    task_target_hash,
)
from backend.crawler.workers.heartbeats import (
    heartbeat_worker,
    mark_worker_stopped,
    register_worker,
)


STATIC_TASK_TYPES = ("static_fetch", "sitemap_fetch", "feed_fetch")


@dataclass(frozen=True, slots=True)
class PreparedStaticTask:
    fetch: HttpFetchResult
    html: HtmlDocument | None
    metadata: dict | None
    links: tuple[DiscoveredCandidate, ...]


@dataclass(frozen=True, slots=True)
class WorkerOutcome:
    state: str
    task_uid: str | None = None
    result_uid: str | None = None
    error_code: str | None = None


def _candidate(
    url: str,
    *,
    source_url: str,
    depth: int,
    relation_type: str,
    discovery_type: str,
    task_type: str,
    max_depth: int,
    extra: dict | None = None,
) -> DiscoveredCandidate | None:
    try:
        normalized = normalize_http_url(url)
        source = normalize_http_url(source_url)
    except (InvalidUrl, ValueError):
        return None
    internal = same_origin(source, normalized)
    metadata = {"task_type": task_type}
    if extra:
        metadata.update(extra)
    return DiscoveredCandidate(
        discovered_url=normalized.url,
        normalized_url=normalized.url,
        relation_type=relation_type,
        discovery_type=discovery_type,
        depth=depth,
        same_origin=internal,
        enqueue=internal and depth <= max_depth,
        metadata=metadata,
    )


class StaticTaskHandler:
    def __init__(self, *, fetcher: StaticHttpFetcher, settings: CrawlerSettings) -> None:
        self.fetcher = fetcher
        self.settings = settings

    def _validated_payload(self, task: CrawlTask) -> tuple[dict, str, int, int]:
        payload = task.payload_json
        if not isinstance(payload, dict):
            raise CrawlerError("invalid_url", "static task payload is missing")
        payload = dict(payload)
        target = payload.get("target_url")
        depth = payload.get("depth")
        if (
            not isinstance(target, str)
            or not isinstance(depth, int)
            or isinstance(depth, bool)
            or depth < 0
        ):
            raise CrawlerError("invalid_url", "static task payload is invalid")
        try:
            normalized = normalize_http_url(target)
        except (InvalidUrl, ValueError) as error:
            raise CrawlerError("invalid_url", "static task URL is invalid") from error
        expected = payload.get("normalized_url")
        if expected is not None and expected != normalized.url:
            raise CrawlerError("invalid_url", "static task normalized URL does not match")
        max_depth = payload.get("max_depth", self.settings.max_depth)
        max_pages = payload.get("max_pages", self.settings.max_pages_per_origin)
        max_links = payload.get("max_links_per_page", self.settings.max_links_per_page)
        sitemap_depth = payload.get("sitemap_depth", 0)
        if (
            not isinstance(max_depth, int)
            or isinstance(max_depth, bool)
            or max_depth < 1
            or not isinstance(max_pages, int)
            or isinstance(max_pages, bool)
            or max_pages < 1
            or not isinstance(max_links, int)
            or isinstance(max_links, bool)
            or max_links < 1
            or not isinstance(sitemap_depth, int)
            or isinstance(sitemap_depth, bool)
            or sitemap_depth < 0
            or payload.get("discovery_policy", "same_origin") != "same_origin"
        ):
            raise CrawlerError("invalid_url", "static task depth limit is invalid")
        payload["max_pages"] = min(max_pages, self.settings.max_pages_per_origin)
        payload["max_links_per_page"] = min(max_links, self.settings.max_links_per_page)
        payload["sitemap_depth"] = min(sitemap_depth, self.settings.max_sitemap_depth)
        return payload, normalized.url, depth, min(max_depth, self.settings.max_depth)

    def prepare(self, task: CrawlTask, cancel_event: threading.Event) -> PreparedStaticTask:
        if task.task_type not in STATIC_TASK_TYPES:
            raise CrawlerError("invalid_url", "unsupported static crawler task type")
        payload, target, depth, max_depth = self._validated_payload(task)
        fetched = self.fetcher.fetch(target, cancel_event=cancel_event)
        html: HtmlDocument | None = None
        metadata: dict | None = None
        candidates: list[DiscoveredCandidate] = []

        if fetched.content_type in {"text/html", "application/xhtml+xml"}:
            html = parse_html(fetched.body, final_url=fetched.final_url, charset=fetched.charset)
            policy = DiscoveryPolicy(
                max_depth=max_depth,
                max_links_per_page=min(
                    int(payload.get("max_links_per_page", self.settings.max_links_per_page)),
                    self.settings.max_links_per_page,
                ),
            )
            candidates.extend(
                select_discovered_links(
                    html.links,
                    source_url=fetched.final_url,
                    depth=depth,
                    policy=policy,
                )
            )
            for feed_url in html.feed_urls:
                item = _candidate(
                    feed_url,
                    source_url=fetched.final_url,
                    depth=depth + 1,
                    relation_type="alternate",
                    discovery_type="html_feed",
                    task_type="feed_fetch",
                    max_depth=max_depth,
                )
                if item:
                    candidates.append(item)
            sitemap_urls = list(html.sitemap_urls)
            if fetched.robots is not None:
                sitemap_urls.extend(fetched.robots.sitemaps)
            if depth == 0:
                sitemap_urls.append(urljoin(normalize_http_url(fetched.final_url).origin + "/", "sitemap.xml"))
            for sitemap_url in sitemap_urls:
                item = _candidate(
                    sitemap_url,
                    source_url=fetched.final_url,
                    depth=depth + 1,
                    relation_type="sitemap",
                    discovery_type="sitemap_hint",
                    task_type="sitemap_fetch",
                    max_depth=max_depth,
                    extra={"sitemap_depth": 0},
                )
                if item:
                    candidates.append(item)
        elif task.task_type == "feed_fetch" or fetched.content_type in {
            "application/rss+xml",
            "application/atom+xml",
        }:
            feed = parse_feed(
                fetched.body,
                source_url=fetched.final_url,
                max_entries=self.settings.max_feed_entries,
            )
            metadata = self._feed_metadata(feed)
            for entry in feed.entries:
                item = _candidate(
                    entry.link,
                    source_url=fetched.final_url,
                    depth=depth + 1,
                    relation_type="feed_entry",
                    discovery_type="feed",
                    task_type="static_fetch",
                    max_depth=max_depth,
                    extra={"title": entry.title or "", "published": entry.published or entry.updated or ""},
                )
                if item:
                    candidates.append(item)
        else:
            try:
                sitemap = parse_sitemap(
                    fetched.body,
                    source_url=fetched.final_url,
                    max_bytes=self.settings.max_sitemap_bytes,
                    max_urls=self.settings.max_sitemap_urls,
                )
            except SitemapError as error:
                if task.task_type == "static_fetch":
                    feed = parse_feed(
                        fetched.body,
                        source_url=fetched.final_url,
                        max_entries=self.settings.max_feed_entries,
                    )
                    metadata = self._feed_metadata(feed)
                    if feed.parse_error and not feed.entries:
                        raise CrawlerError("http_4xx", "XML document is neither sitemap nor feed") from error
                else:
                    raise CrawlerError("http_4xx", "sitemap parsing failed") from error
            else:
                metadata = {"document_type": sitemap.kind, "url_count": len(sitemap.urls), "sitemap_count": len(sitemap.sitemaps)}
                candidates.extend(self._sitemap_candidates(sitemap, fetched.final_url, depth, max_depth, payload))

        unique: dict[str, DiscoveredCandidate] = {}
        for item in candidates:
            unique.setdefault(item.normalized_url, item)
        return PreparedStaticTask(fetched, html, metadata, tuple(unique.values()))

    @staticmethod
    def _feed_metadata(feed: FeedDocument) -> dict:
        return {
            "document_type": "feed",
            "title": feed.title,
            "site_link": feed.site_link,
            "entry_count": len(feed.entries),
            "parse_error": feed.parse_error,
        }

    def _sitemap_candidates(
        self,
        sitemap: SitemapDocument,
        source_url: str,
        depth: int,
        max_depth: int,
        payload: dict,
    ) -> list[DiscoveredCandidate]:
        candidates: list[DiscoveredCandidate] = []
        for location in sitemap.urls:
            item = _candidate(
                location.url,
                source_url=source_url,
                depth=depth + 1,
                relation_type="sitemap_url",
                discovery_type="sitemap",
                task_type="static_fetch",
                max_depth=max_depth,
                extra={"last_modified": location.last_modified or ""},
            )
            if item:
                candidates.append(item)
        sitemap_depth = int(payload.get("sitemap_depth", 0))
        for location in sitemap.sitemaps:
            item = _candidate(
                location.url,
                source_url=source_url,
                depth=depth,
                relation_type="sitemap_index",
                discovery_type="sitemap",
                task_type="sitemap_fetch",
                max_depth=max_depth,
                extra={"sitemap_depth": sitemap_depth + 1},
            )
            if item and sitemap_depth + 1 <= self.settings.max_sitemap_depth:
                candidates.append(item)
            elif item:
                candidates.append(replace(item, enqueue=False, metadata={**item.metadata, "limit": "sitemap_depth"}))
        return candidates

    def _run_tasks(self, session: Session, task: CrawlTask) -> list[CrawlTask]:
        query = select(CrawlTask).where(CrawlTask.task_type.in_(STATIC_TASK_TYPES))
        if task.run_id is not None:
            query = query.where(CrawlTask.run_id == task.run_id)
            return list(session.scalars(query).all())
        run_uid = (task.payload_json or {}).get("run_uid")
        return [
            item
            for item in session.scalars(query).all()
            if isinstance(item.payload_json, dict) and item.payload_json.get("run_uid") == run_uid
        ]

    def persist(
        self,
        session: Session,
        task: CrawlTask,
        prepared: PreparedStaticTask,
        *,
        now: datetime,
    ) -> FetchResult:
        stored = persist_fetch_result(
            session,
            task=task,
            fetch=prepared.fetch,
            document=prepared.html,
            fetched_at=now,
            document_metadata=prepared.metadata,
        ).result
        existing_tasks = self._run_tasks(session, task)
        effective: list[DiscoveredCandidate] = []
        payload = task.payload_json or {}
        run_uid = str(payload.get("run_uid") or "")
        max_depth = min(int(payload.get("max_depth", self.settings.max_depth)), self.settings.max_depth)
        max_pages = min(int(payload.get("max_pages", self.settings.max_pages_per_origin)), self.settings.max_pages_per_origin)
        source_origin = normalize_http_url(prepared.fetch.final_url)

        for candidate in prepared.links:
            item = candidate
            task_type = str(candidate.metadata.get("task_type", "static_fetch"))
            already = next(
                (
                    queued
                    for queued in existing_tasks
                    if queued.task_type == task_type
                    and queued.target_hash == task_target_hash(candidate.normalized_url)
                ),
                None,
            )
            if candidate.enqueue and already is None:
                internal_count = sum(
                    1
                    for queued in existing_tasks
                    if same_origin(source_origin, normalize_http_url(queued.target))
                )
                sitemap_count = sum(1 for queued in existing_tasks if queued.task_type == "sitemap_fetch")
                limit = None
                if len(existing_tasks) >= self.settings.max_urls_per_run:
                    limit = "run_urls"
                elif internal_count >= max_pages:
                    limit = "origin_pages"
                elif task_type == "sitemap_fetch" and sitemap_count >= self.settings.max_sitemap_files:
                    limit = "sitemap_files"
                if limit is not None:
                    item = replace(candidate, enqueue=False, metadata={**candidate.metadata, "limit": limit})
                else:
                    child_payload = {
                        "target_url": candidate.normalized_url,
                        "normalized_url": candidate.normalized_url,
                        "depth": candidate.depth,
                        "parent_url": prepared.fetch.final_url,
                        "run_uid": run_uid,
                        "max_depth": max_depth,
                        "max_pages": max_pages,
                        "discovery_policy": "same_origin",
                    }
                    if "sitemap_depth" in candidate.metadata:
                        child_payload["sitemap_depth"] = candidate.metadata["sitemap_depth"]
                    enqueued = enqueue_discovered_task(
                        session,
                        task_type=task_type,
                        target=candidate.normalized_url,
                        payload=child_payload,
                        run_id=task.run_id,
                    )
                    if enqueued.created:
                        enqueued.task.max_attempts = self.settings.max_attempts
                        existing_tasks.append(enqueued.task)
            effective.append(item)
        persist_discovered_links(
            session,
            result=stored,
            links=tuple(effective),
            discovered_at=now,
        )
        return stored

    def persist_failure(self, session: Session, task: CrawlTask, error: CrawlerError, *, now: datetime) -> FetchResult:
        target = task.target
        if isinstance(task.payload_json, dict):
            target = str(task.payload_json.get("target_url") or target)
        return persist_fetch_failure(
            session,
            task=task,
            target_url=target,
            error_code=error.code,
            error_message=str(error),
            fetched_at=now,
            http_status=error.http_status,
        )


class StaticCrawlerWorker:
    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session],
        handler,
        settings: CrawlerSettings,
        worker_id: str | None = None,
        clock=utc_now,
    ) -> None:
        self.session_factory = session_factory
        self.handler = handler
        self.settings = settings
        self.worker_id = (worker_id or settings.worker_id).strip()
        self.clock = clock

    def _register_and_lease(self) -> CrawlTask | None:
        with self.session_factory.begin() as session:
            now = self.clock()
            register_worker(
                session,
                worker_id=self.worker_id,
                worker_type="static",
                process_id=os.getpid(),
                hostname=socket.gethostname(),
                now=now,
                metadata={"task_types": list(STATIC_TASK_TYPES)},
            )
            retry_due_failed_tasks(session, now=now)
            tasks = lease_tasks(
                session,
                worker_id=self.worker_id,
                task_types=list(STATIC_TASK_TYPES),
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

    def _lease_renewer(
        self,
        task_uid: str,
        stop_event: threading.Event,
        cancel_event: threading.Event,
    ) -> None:
        interval = max(0.5, min(5.0, self.settings.lease_seconds / 3))
        while not stop_event.wait(interval):
            try:
                with self.session_factory.begin() as session:
                    now = self.clock()
                    task = renew_task_lease(
                        session,
                        task_uid=task_uid,
                        worker_id=self.worker_id,
                        lease_seconds=self.settings.lease_seconds,
                        now=now,
                    )
                    if task.run_id is not None:
                        run_status = session.scalar(
                            select(CrawlRun.status).where(CrawlRun.id == task.run_id)
                        )
                        if run_status == STOP_REQUESTED:
                            cancel_event.set()
                            return
                    heartbeat_worker(
                        session,
                        worker_id=self.worker_id,
                        now=now,
                        current_task_uid=task_uid,
                    )
            except (LookupError, ValueError, SQLAlchemyError):
                cancel_event.set()
                return

    def _run_stop_requested(self, task: CrawlTask) -> bool:
        if task.run_id is None:
            return False
        with self.session_factory() as session:
            return session.scalar(
                select(CrawlRun.status).where(CrawlRun.id == task.run_id)
            ) == STOP_REQUESTED

    def _finish_heartbeat(self) -> None:
        with self.session_factory.begin() as session:
            heartbeat_worker(session, worker_id=self.worker_id, now=self.clock())

    def process_one(self, *, cancel_event: threading.Event | None = None) -> WorkerOutcome:
        event = cancel_event or threading.Event()
        task = self._register_and_lease()
        if task is None:
            return WorkerOutcome("empty")
        if event.is_set() or self._run_stop_requested(task):
            with self.session_factory.begin() as session:
                cancel_leased_task(
                    session,
                    task_uid=task.task_uid,
                    worker_id=self.worker_id,
                    now=self.clock(),
                )
            self._finish_heartbeat()
            return WorkerOutcome("cancelled", task.task_uid, error_code="cancelled")
        renew_stop = threading.Event()
        renewer = threading.Thread(
            target=self._lease_renewer,
            args=(task.task_uid, renew_stop, event),
            name=f"lease-renew-{self.worker_id}",
            daemon=True,
        )
        renewer.start()
        try:
            prepared = self.handler.prepare(task, event)
            with self.session_factory.begin() as session:
                current = session.scalar(
                    select(CrawlTask).where(CrawlTask.task_uid == task.task_uid).with_for_update()
                )
                if current is None:
                    raise LookupError("crawler task disappeared")
                result = self.handler.persist(session, current, prepared, now=self.clock())
                if self.settings.analysis_enabled and isinstance(result, FetchResult):
                    enqueue_analysis_task(
                        session,
                        fetch_result=result,
                        run_id=current.run_id,
                        analysis_version=self.settings.analysis_rule_version,
                        spec=AnalysisSpec(
                            analyzer_type=self.settings.analyzer_type,
                            provider_name=self.settings.analysis_provider,
                            model_version=self.settings.analysis_model_version,
                            prompt_version=self.settings.analysis_prompt_version,
                            taxonomy_version=self.settings.analysis_taxonomy_version,
                            scoring_version=self.settings.analysis_scoring_version,
                            schema_version=self.settings.analysis_schema_version,
                        ),
                        max_attempts=self.settings.max_attempts,
                        available_at=self.clock(),
                    )
                complete_task(
                    session,
                    task_uid=task.task_uid,
                    worker_id=self.worker_id,
                    now=self.clock(),
                )
                result_uid = getattr(result, "result_uid", None)
            return WorkerOutcome("completed", task.task_uid, result_uid)
        except Cancelled as error:
            with self.session_factory.begin() as session:
                cancel_leased_task(
                    session,
                    task_uid=task.task_uid,
                    worker_id=self.worker_id,
                    now=self.clock(),
                )
            return WorkerOutcome("cancelled", task.task_uid, error_code=error.code)
        except SQLAlchemyError:
            raise
        except CrawlerError as error:
            with self.session_factory.begin() as session:
                current = session.scalar(select(CrawlTask).where(CrawlTask.task_uid == task.task_uid))
                if current is None:
                    raise LookupError("crawler task disappeared")
                persist_failure = getattr(self.handler, "persist_failure", None)
                if persist_failure is not None:
                    persist_failure(session, current, error, now=self.clock())
                failed = fail_task(
                    session,
                    task_uid=task.task_uid,
                    worker_id=self.worker_id,
                    error_code=error.code,
                    error_message=str(error),
                    now=self.clock(),
                    retryable=error.retryable,
                )
            return WorkerOutcome(
                "dead" if failed.status == DEAD else "retry_wait",
                task.task_uid,
                error_code=error.code,
            )
        except Exception as error:
            with self.session_factory.begin() as session:
                failed = fail_task(
                    session,
                    task_uid=task.task_uid,
                    worker_id=self.worker_id,
                    error_code="internal_error",
                    error_message=str(error),
                    now=self.clock(),
                    retryable=True,
                )
            return WorkerOutcome(
                "dead" if failed.status == DEAD else "retry_wait",
                task.task_uid,
                error_code="internal_error",
            )
        finally:
            renew_stop.set()
            renewer.join(timeout=2)
            self._finish_heartbeat()

    def run(self, *, max_jobs: int, cancel_event: threading.Event | None = None) -> tuple[WorkerOutcome, ...]:
        if max_jobs < 1:
            raise ValueError("worker job limit must be positive")
        event = cancel_event or threading.Event()
        outcomes: list[WorkerOutcome] = []
        try:
            empty_polls = 0
            while len(outcomes) < max_jobs and not event.is_set():
                outcome = self.process_one(cancel_event=event)
                if outcome.state == "empty":
                    empty_polls += 1
                    if empty_polls >= 3 or event.wait(0.1):
                        break
                    continue
                empty_polls = 0
                outcomes.append(outcome)
        finally:
            try:
                with self.session_factory.begin() as session:
                    mark_worker_stopped(session, worker_id=self.worker_id, now=self.clock())
            except LookupError:
                pass
        return tuple(outcomes)


__all__ = [
    "PreparedStaticTask",
    "STATIC_TASK_TYPES",
    "StaticCrawlerWorker",
    "StaticTaskHandler",
    "WorkerOutcome",
]
