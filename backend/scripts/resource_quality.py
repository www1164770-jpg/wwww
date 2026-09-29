"""Read-only by default. Writes are restricted to explicit isolated test DBs."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(1, str(Path(__file__).resolve().parents[2]))
from sqlalchemy import create_engine, text, inspect, select
from sqlalchemy.engine import URL
from sqlalchemy.schema import CreateTable
from resource_quality import audit_resources
from resource_migration import (VERSION, snapshot, metadata, approved_tag_plan,
    maintenance_plan, apply_plan, rollback_plan, rollback, ReviewIdentityDrift, change_key, claims)
from resource_fields import effective_fields
from v3_tag_identity import MAPPING_VERSION


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["audit", "tags-preview", "tags-apply", "maintenance-preview", "maintenance-apply", "rollback-preview", "rollback"])
    parser.add_argument("--input", type=Path, default=Path("docs/recommendation/v3-tag-review-queue.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--test-database", action="store_true", help="Use RESOURCE_TEST_DATABASE_URL, never the application DB")
    parser.add_argument("--preview", type=Path, help="Previously generated preview, required before any write")
    parser.add_argument("--source-review", type=Path, default=Path("docs/recommendation/v3-tag-review-queue.json"))
    parser.add_argument("--migration-version", choices=[VERSION, MAPPING_VERSION], default=VERSION)
    args = parser.parse_args()
    writing = args.command in {"tags-apply", "maintenance-apply", "rollback"}
    document = None
    source_queue = None
    version = args.migration_version
    if args.command.startswith("tags") or args.command.startswith("maintenance"):
        document = json.loads(args.input.read_text(encoding="utf-8"))
        if isinstance(document, dict) and document.get("mode") == "mapped_approved_subset":
            version = MAPPING_VERSION
            source_queue = json.loads(args.source_review.read_text(encoding="utf-8"))
    if writing and not args.test_database:
        parser.error("Writes require --test-database; application/production writes are disabled")
    reviewed_preview = None
    if writing:
        if not args.preview:
            parser.error("Generate and inspect a preview first, then supply --preview")
        reviewed_preview = json.loads(args.preview.read_text(encoding="utf-8"))
    if args.test_database:
        dsn = os.environ.get("RESOURCE_TEST_DATABASE_URL")
        if not dsn:
            parser.error("Set RESOURCE_TEST_DATABASE_URL to an isolated test database")
        engine = create_engine(dsn)
        if engine.url.get_backend_name() != "sqlite" and not (engine.url.database or "").endswith("_test"):
            parser.error("Test database name must end in _test")
        if engine.url.host not in (None, "localhost", "127.0.0.1", "::1"):
            parser.error("Only local test database writes are supported")
    else:
        from db_pool import validate_database_config
        config = validate_database_config()
        engine = create_engine(URL.create("mysql+pymysql", username=config["user"], password=config["password"],
            host=config["host"], port=config["port"], database=config["database"]),
            connect_args={"charset": "utf8mb4", "connect_timeout": 4, "read_timeout": 10})
    report = {"version": version, "command": args.command, "database": engine.url.database,
              "captured_at": datetime.now(timezone.utc).isoformat(), "database_write_performed": False}
    if writing and (reviewed_preview.get("version") != version or
                    reviewed_preview.get("database") != engine.url.database or reviewed_preview.get("blocked")):
        parser.error("Preview version/database mismatch, or preview contains blocked identities")
    with engine.connect() as conn:
        if writing:
            # MySQL DDL implicitly commits; additive tables are created before
            # the atomic DML transaction, never mixed into its rollback promise.
            metadata.create_all(conn)
            conn.commit()
        elif engine.dialect.name == "mysql":
            conn.exec_driver_sql("SET TRANSACTION READ ONLY")
            conn.exec_driver_sql("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
        elif engine.dialect.name == "sqlite":
            conn.exec_driver_sql("PRAGMA query_only=ON")
        locked = False
        try:
            if writing and engine.dialect.name == "mysql":
                locked = conn.execute(text("SELECT GET_LOCK('resource_quality_20260924', 10)")).scalar() == 1
                if not locked:
                    raise RuntimeError("Could not acquire migration lock")
            if args.command.startswith("rollback"):
                current = rollback_plan(conn, version=version)
                if writing and current != reviewed_preview.get("changes"):
                    raise ValueError("Rollback state changed; generate a fresh preview")
                report["changes"] = rollback(conn, version=version) if writing else current
            else:
                data = snapshot(conn)
                if args.command == "audit":
                    report.update(audit_resources(data["websites"], data["site_tags"], data["tags"], data["site_occupations"]))
                    field_rows = list(conn.execute(select(claims)).mappings()) if inspect(conn).has_table(claims.name) else []
                    grouped = {}
                    for row in field_rows:
                        grouped.setdefault(row["site_id"], []).append(row)
                    resolved = [effective_fields(grouped.get(site["id"], [])) for site in data["websites"]]
                    report["structured_field_coverage"] = {field: {
                        "recorded_resources": sum(bool(fields.get(field, {}).get("value")) for fields in resolved),
                        "verified_resources": sum(bool(fields.get(field, {}).get("value") and fields.get(field, {}).get("verified_at")) for fields in resolved),
                    } for field in ("audience", "pricing_model", "language", "entry_requirements")}
                    report["unknown_structured_fields"] = [field for field, counts in report["structured_field_coverage"].items() if not counts["recorded_resources"]]
                else:
                    try:
                        plan = approved_tag_plan(document, data, source_queue=source_queue) if args.command.startswith("tags") else maintenance_plan(document, data)
                    except ReviewIdentityDrift as error:
                        report["blocked"] = str(error)
                        report["identity_conflicts"] = error.conflicts
                        report["rollback_preview"] = []
                        plan = []
                        if writing:
                            raise
                    report["plan"] = plan
                    report["already_present"] = None if report.get("blocked") else sum(item.get("already_present", False) for item in plan)
                    report["pending"] = None if report.get("blocked") else sum(not item.get("already_present", False) for item in plan)
                    report["schema_preview"] = [str(CreateTable(table, if_not_exists=True).compile(engine)) for table in metadata.sorted_tables]
                    report["rollback_preview"] = "Remove only journal-owned site_tags IDs; mark owned claims/identity links reverted. Retain websites, favorites, history, tag dictionary and journal."
                    if writing:
                        if [change_key(row) for row in plan] != [change_key(row) for row in reviewed_preview.get("plan", [])]:
                            raise ValueError("Plan changed; generate a fresh preview")
                        report["applied"] = apply_plan(conn, plan, version=version)
            if writing:
                conn.commit()
                report["database_write_performed"] = True
            else:
                conn.rollback()
        except Exception:
            conn.rollback()
            raise
        finally:
            if locked:
                conn.execute(text("SELECT RELEASE_LOCK('resource_quality_20260924')"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key in
        {"version", "command", "database_write_performed", "total_resources", "already_present", "pending"}}))


if __name__ == "__main__":
    main()
