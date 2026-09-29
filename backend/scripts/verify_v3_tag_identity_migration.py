"""Validate the real resolved subset in a NEW local MySQL test schema only."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]
import pymysql
from sqlalchemy import (create_engine, MetaData, Table, Column, Integer, String, Text, select)
from sqlalchemy.engine import URL
from db_pool import validate_database_config
from resource_migration import metadata, snapshot, approved_tag_plan, apply_plan, rollback_plan, journal
from v3_tag_identity import MAPPING_VERSION


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create-isolated-test-db", action="store_true", required=True)
    parser.add_argument("--mapping-dir", type=Path, default=ROOT / "docs/recommendation/v3-tag-identity-20260925")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/data/stage1-tag-identity-mysql-test.json")
    args = parser.parse_args()
    source_queue_path = ROOT / "docs/recommendation/v3-tag-review-queue.json"
    source_queue = json.loads(source_queue_path.read_text(encoding="utf-8"))
    data = json.loads((args.mapping_dir / "catalog-snapshot.json").read_text(encoding="utf-8"))["data"]
    mapped_path = args.mapping_dir / "resolved-review.json"
    mapped = json.loads(mapped_path.read_text(encoding="utf-8"))
    original_plan = approved_tag_plan(mapped, data, source_queue=source_queue)
    original_existing = sum(row["already_present"] for row in original_plan)
    expected_new = len(original_plan) - original_existing - 1
    config = validate_database_config()
    if config["host"] not in ("localhost", "127.0.0.1", "::1"):
        raise ValueError("Only a local MySQL test schema is permitted")
    target = "v3_tag_identity_" + uuid4().hex[:12] + "_test"
    with pymysql.connect(**config) as conn, conn.cursor() as cursor:
        cursor.execute(f"CREATE DATABASE `{target}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    url = URL.create("mysql+pymysql", username=config["user"], password=config["password"],
                     host=config["host"], port=config["port"], database=target, query={"charset": "utf8mb4"})
    engine = create_engine(url)
    fixture = MetaData()
    sites = Table("websites", fixture, Column("id", Integer, primary_key=True), Column("name", String(100)),
        Column("url", String(500)), Column("status", String(20)), Column("source", String(50)), Column("aliases", Text))
    tags = Table("tags", fixture, Column("id", Integer, primary_key=True), Column("name", String(80), unique=True), Column("type", String(32)))
    links = Table("site_tags", fixture, Column("id", Integer, primary_key=True), Column("site_id", Integer), Column("tag_id", Integer))
    Table("site_occupations", fixture, Column("id", Integer, primary_key=True), Column("site_id", Integer), Column("occupation", String(64)))
    folder = ROOT / "artifacts" / target
    folder.mkdir(parents=True)
    report = {"test_database": target, "source_database_modified": False, "user_data_copied": False,
              "migration_version": MAPPING_VERSION, "source_plan_unique_pairs": len(original_plan), "checks": []}
    def check(value, message):
        if not value:
            raise AssertionError(message)
        report["checks"].append(message)
    try:
        fixture.create_all(engine)
        metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(sites.insert(), data["websites"])
            conn.execute(tags.insert(), [{key: row.get(key) for key in ("id", "name", "type")} for row in data["tags"]])
            conn.execute(links.insert(), data["site_tags"])
            # A prior batch owns one already-approved pair. The new rollback
            # must preserve it, plus every original catalog association.
            prior = dict(next(row for row in original_plan if not row["already_present"]))
            apply_plan(conn, [prior], version="prior_fixture_batch")
            before_links = {tuple(row) for row in conn.execute(select(links)).all()}
            before_tags = {tuple(row) for row in conn.execute(select(tags)).all()}
            expected = approved_tag_plan(mapped, snapshot(conn), source_queue=source_queue)
            check(sum(row["already_present"] for row in expected) == original_existing + 1, "Original approved associations plus one prior-batch fixture are recognized")
        env = dict(os.environ, RESOURCE_TEST_DATABASE_URL=url.render_as_string(hide_password=False), PYTHONIOENCODING="utf-8")
        def cli(command, output, preview=None):
            argv = [sys.executable, str(ROOT / "backend/scripts/resource_quality.py"), command, "--test-database",
                "--input", str(mapped_path), "--source-review", str(source_queue_path), "--migration-version", MAPPING_VERSION,
                "--output", str(folder / output)]
            if preview:
                argv += ["--preview", str(folder / preview)]
            result = subprocess.run(argv, env=env, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            if result.returncode:
                raise RuntimeError(f"{command} failed; exit={result.returncode}")
            return json.loads((folder / output).read_text(encoding="utf-8"))
        preview = cli("tags-preview", "migration-preview.json")
        check(preview["already_present"] == original_existing + 1 and preview["pending"] == expected_new, "Revised preview skips original and prior approved associations")
        first = cli("tags-apply", "first-apply.json", "migration-preview.json")
        check(len(first["applied"]) == expected_new, "CLI applies precisely the missing approved subset")
        again = cli("tags-apply", "second-apply.json", "migration-preview.json")
        check(again["applied"] == [], "Identical CLI migration is idempotent")
        with engine.connect() as conn:
            after = {tuple(row) for row in conn.execute(select(links)).all()}
            check(before_links <= after and len(after - before_links) == expected_new, "No original link was changed or removed")
            check(all(row["already_present"] for row in approved_tag_plan(mapped, snapshot(conn), source_queue=source_queue)), "Every reliably mapped approved code is now present in the test DB")
            check(len(rollback_plan(conn, version="prior_fixture_batch")) == 1, "Other migration version remains active")
        down = cli("rollback-preview", "rollback-preview.json")
        check(len(down["changes"]) == expected_new, "Rollback preview owns only this migration's inserted links")
        cli("rollback", "rollback-result.json", "rollback-preview.json")
        with engine.connect() as conn:
            check({tuple(row) for row in conn.execute(select(links)).all()} == before_links, "Rollback exactly restores original and prior-batch associations")
            check(before_tags <= {tuple(row) for row in conn.execute(select(tags)).all()}, "Rollback deletes no existing tag dictionary row")
            check(len(rollback_plan(conn, version="prior_fixture_batch")) == 1 and rollback_plan(conn, version=MAPPING_VERSION) == [], "Rollback is isolated to the new version")
        cli("rollback-preview", "empty-rollback-preview.json")
        twice = cli("rollback", "second-rollback.json", "empty-rollback-preview.json")
        check(twice["changes"] == [], "Repeated rollback is a no-op")
        report.update(status="passed", new_associations=len(first["applied"]), protected_existing_associations=len(before_links), artifacts=str(folder.relative_to(ROOT)))
    except Exception as exc:
        report.update(status="failed", failure=type(exc).__name__ + ": " + str(exc))
        raise
    finally:
        engine.dispose()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"database": target, "status": report.get("status"), "checks": len(report["checks"])}))


if __name__ == "__main__":
    main()
