"""Serialized, restartable index projection using crawler outbox leases.

Events are wake-ups, never stale document payloads. Every batch projects a fresh
consistent catalog. A durable task slot fences subsequent submissions on timeout.
Ambiguous submissions fail closed until explicit recovery drains engine tasks.
"""
from contextlib import contextmanager
from datetime import timedelta
import time
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from backend.crawler.db import OutboxEvent, utc_now
from backend.crawler.outbox.service import lease_outbox_events, mark_outbox_processed, fail_outbox_event
from search_service import SETTINGS, document, public, SearchUnavailable, SearchConfigurationError


class Sync:
    def __init__(self, catalog, meili):
        self.catalog, self.engine, self.meili = catalog, catalog.engine, meili
        self.owner = "search-" + uuid4().hex

    @contextmanager
    def lock(self):
        # One lock per database, across all workers, retries and rebuild commands.
        with self.engine.connect() as conn:
            name = "search-sync:" + self.engine.url.database
            if conn.execute(text("SELECT GET_LOCK(:name,0)"), {"name": name}).scalar() != 1:
                raise SearchUnavailable("search_worker_busy")
            conn.commit()
            try:
                self.lock_connection = conn
                yield
            finally:
                conn.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": name})
                conn.commit()

    def state(self):
        with self.engine.connect() as conn:
            return dict(conn.execute(text("SELECT * FROM search_sync_state WHERE id=1")).mappings().one())

    def save(self, **values):
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE search_sync_state SET " + ",".join(f"{k}=:{k}" for k in values) + " WHERE id=1"), values)

    def resume(self):
        state = self.state()
        if state["task_id"] == -1:
            raise SearchUnavailable("ambiguous_submission_requires_recover")
        if state["task_id"] is not None:
            try:
                self.meili.wait(state["task_id"])
            except SearchConfigurationError:
                self.save(task_id=None, task_kind=None)
                raise
            self.save(task_id=None, task_kind=None)

    def task(self, method, path, body, kind="projection", target=None):
        self.resume()
        # Check lock connection is still alive BEFORE every mutation.
        self.lock_connection.execute(text("SELECT 1"))
        self.lock_connection.commit()
        self.save(task_id=-1, task_kind=kind, target_index=target, indexed_revision=-1)
        try:
            response = self.meili.request(method, path, body)
        except SearchConfigurationError:
            # Definite HTTP rejection cannot have queued a task.
            self.save(task_id=None, task_kind=None)
            raise
        self.save(task_id=response["taskUid"])
        self.resume()

    def reconcile(self, index=None):
        revision, _, rows = self.catalog.snapshot()
        expected = {r["id"]: document(r) for r in rows if public(r)}
        actual = {int(r["id"]): r for r in self.meili.documents(index)}
        return {"revision": revision, "missing": sorted(expected.keys()-actual.keys()),
                "not_public_or_removed": sorted(actual.keys()-expected.keys()),
                "stale": sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k]),
                "expected_count": len(expected), "actual_count": len(actual)}

    def project(self, index):
        revision, _, rows = self.catalog.snapshot()
        docs = [document(r) for r in rows if public(r)]
        if len(docs) >= SETTINGS["pagination"]["maxTotalHits"]:
            raise SearchConfigurationError("catalog_exceeds_validated_search_capacity")
        actual_ids = {int(r["id"]) for r in self.meili.documents(index)}
        self.task("PATCH", f"/indexes/{index}/settings", SETTINGS, target=index)
        if docs:
            self.task("PUT", f"/indexes/{index}/documents?primaryKey=id", docs, target=index)
        removed = sorted(actual_ids - {r["id"] for r in docs})
        if removed:
            self.task("POST", f"/indexes/{index}/documents/delete-batch", removed, target=index)
        return revision

    def once(self):
        with self.lock():
            self.resume()
            now = utc_now()
            with Session(self.engine) as session, session.begin():
                expired = session.scalars(select(OutboxEvent).where(OutboxEvent.event_type == "search.changed",
                    OutboxEvent.status == "leased", OutboxEvent.leased_until <= now).with_for_update()).all()
                for event in expired:
                    # A crashed worker consumes an attempt and cannot loop forever.
                    fail_outbox_event(session, event_uid=event.event_uid, worker_id=event.worker_id,
                        error_message="lease_expired", now=now)
                events = lease_outbox_events(session, worker_id=self.owner, limit=100,
                    lease_seconds=120, now=now, event_type="search.changed")
                uids = [event.event_uid for event in events]
            if not uids:
                return {"processed": 0}
            try:
                revision = self.project(self.meili.index)
                # Only confirmed tasks advance the cache generation. Committed
                # changes after snapshot have a higher revision and stay pending.
                self.save(indexed_revision=revision)
                with Session(self.engine) as session, session.begin():
                    for uid in uids:
                        mark_outbox_processed(session, event_uid=uid, worker_id=self.owner, now=utc_now())
                return {"processed": len(uids), "indexed_revision": revision}
            except Exception as exc:
                with Session(self.engine) as session, session.begin():
                    for uid in uids:
                        fail_outbox_event(session, event_uid=uid, worker_id=self.owner,
                            error_message=type(exc).__name__ + ": " + str(exc) if isinstance(exc, (SearchUnavailable, SearchConfigurationError)) else type(exc).__name__, now=utc_now())
                raise

    def retry(self):
        with self.lock(), Session(self.engine) as session, session.begin():
            events = session.scalars(select(OutboxEvent).where(OutboxEvent.event_type == "search.changed", OutboxEvent.status == "dead").with_for_update()).all()
            for event in events:
                event.status, event.attempt_count, event.available_at = "pending", 0, utc_now().replace(microsecond=0)
                # Keep last_error as historical evidence until successful processing.
            return {"retried": len(events)}

    def recover(self):
        with self.lock():
            # After a transport timeout the server might have accepted a request.
            # Drain ALL pending tasks before releasing the durable submission fence.
            # Never repeat a swap blindly: fresh reconciliation determines state.
            while True:
                page = self.meili.request("GET", "/tasks?statuses=enqueued,processing&limit=100")
                if not page["results"]:
                    break
                for task in page["results"]:
                    try:
                        self.meili.wait(task["uid"])
                    except SearchConfigurationError:
                        pass  # terminal failure is drained, not successful indexing
            self.save(task_id=None, task_kind=None, indexed_revision=-1)
            return {"recovered": True, "next": "retry, then worker/rebuild to reconcile current state"}

    def rebuild(self, during_build=None):
        with self.lock():
            self.resume()
            temporary = self.meili.index + "_build_" + uuid4().hex[:12]
            self.task("POST", "/indexes", {"uid": temporary, "primaryKey": "id"}, target=temporary)
            self.project(temporary)
            if during_build:
                during_build()
            # Re-read after build, include increments committed during initial load.
            revision = self.project(temporary)
            # Validate against the exact projected version. If writes race this
            # check, retry build; live index is untouched.
            check = self.reconcile(temporary)
            if check["revision"] != revision or any(check[k] for k in ("missing", "stale", "not_public_or_removed")):
                raise SearchUnavailable("catalog_changed_during_rebuild_retry")
            settings = self.meili.request("GET", f"/indexes/{temporary}/settings")
            if any((sorted(settings.get(k, [])) != sorted(v) if k in ("filterableAttributes", "sortableAttributes") else settings.get(k) != v) for k,v in SETTINGS.items()):
                raise SearchConfigurationError("rebuilt_settings_mismatch")
            self.task("POST", "/swap-indexes", [{"indexes": [self.meili.index, temporary]}], kind="swap", target=temporary)
            self.save(indexed_revision=revision)
            # Old index retained under temporary name. All concurrent outbox
            # events remain unprocessed; a higher DB version bypasses stale cache.
            return {"swapped": True, "retained_previous_index": temporary, "indexed_revision": revision}
