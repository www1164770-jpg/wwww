"""Search operations; mutations require an explicitly isolated local test DB.

Application worker execution is a separate opt-in (SEARCH_SYNC_ENABLED=1).
Migration/rebuild commands never silently target the application database.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.schema import CreateTable
from search_catalog import Catalog, engine_from_environment
from search_service import Meili
from search_migration import preview, apply
from search_sync import Sync
from backend.crawler.db import OutboxEvent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migration-preview", "migration-apply", "migration-rollback-preview", "migration-rollback", "reconcile", "initialize-index", "rebuild", "once", "worker", "retry", "recover", "status"])
    parser.add_argument("--test-database", action="store_true")
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.test_database:
        dsn = os.environ.get("SEARCH_TEST_DATABASE_URL")
        if not dsn:
            parser.error("SEARCH_TEST_DATABASE_URL is required")
        engine = create_engine(dsn, isolation_level="READ COMMITTED", pool_pre_ping=True)
        if engine.url.host not in ("localhost", "127.0.0.1", "::1") or not (engine.url.database or "").endswith("_test"):
            parser.error("Only a local isolated *_test schema is permitted")
        index = os.getenv("SEARCH_TEST_INDEX", "")
        if not index.startswith("stage2_test_"):
            parser.error("SEARCH_TEST_INDEX must start with stage2_test_")
    else:
        if args.command not in ("migration-preview", "migration-rollback-preview", "reconcile", "status", "worker"):
            parser.error("Mutations require --test-database; application database maintenance is disabled")
        if args.command == "worker" and os.getenv("SEARCH_SYNC_ENABLED") != "1":
            parser.error("Worker requires explicit SEARCH_SYNC_ENABLED=1 and a reviewed migration")
        engine = engine_from_environment()
        index = os.getenv("MEILI_INDEX", "websites")
    meili = Meili(os.getenv("MEILI_HOST", "http://127.0.0.1:7700"), os.getenv("MEILI_MASTER_KEY"), index)
    sync = Sync(Catalog(engine), meili)
    if args.command.startswith("migration"):
        with engine.connect() as conn:
            result = preview(conn)
            result["outbox_table"] = str(CreateTable(OutboxEvent.__table__, if_not_exists=True).compile(engine))
            if args.command.startswith("migration-rollback"):
                result = {"version":result["version"],"database":result["database"],"rollback":result["rollback"],"policy":result["rollback_policy"]}
                if args.command == "migration-rollback":
                    if not args.preview or json.loads(args.preview.read_text(encoding="utf-8")) != result:
                        parser.error("Inspect matching rollback --preview first")
                    with sync.lock():
                        for sql in result["rollback"]:
                            conn.exec_driver_sql(sql)
                        conn.commit()
                    result["applied"] = True
            if args.command == "migration-apply":
                if not args.preview or json.loads(args.preview.read_text(encoding="utf-8")) != result:
                    parser.error("Generate and inspect matching --preview before migration")
                apply(conn, preview(conn))
                result["applied"] = True
    elif args.command == "status":
        result = sync.state()
        with engine.connect() as conn:
            result["outbox"] = [dict(r) for r in conn.execute(text("SELECT status,COUNT(*) AS count FROM outbox_events WHERE event_type='search.changed' GROUP BY status")).mappings()]
            result["failures"] = [dict(r) for r in conn.execute(text("SELECT event_uid,status,attempt_count,last_error FROM outbox_events WHERE event_type='search.changed' AND last_error IS NOT NULL ORDER BY id DESC LIMIT 100")).mappings()]
    elif args.command == "initialize-index":
        # Explicit creation only: existing-index errors remain visible, no deletion.
        with sync.lock():
            sync.task("POST", "/indexes", {"uid":index,"primaryKey":"id"},target=index)
        result = {"created":index,"next":"rebuild before enabling indexed reads"}
    elif args.command == "worker":
        while True:
            try:
                print(json.dumps(sync.once()), flush=True)
            except Exception as exc:
                print(json.dumps({"sync_pending": True, "error_type": type(exc).__name__}), flush=True)
            time.sleep(2)
    else:
        result = getattr(sync, args.command)()
    serialized = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
