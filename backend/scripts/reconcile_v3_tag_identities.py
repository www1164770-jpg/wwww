"""Read current catalog or a recorded catalog snapshot; never write a database."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT)]
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import URL
from resource_migration import snapshot, approved_tag_plan
from v3_tag_identity import resolve_review_queue, MAPPING_VERSION


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=ROOT / "docs/recommendation/v3-tag-review-queue.json")
    parser.add_argument("--snapshot", type=Path, help="Replay a recorded snapshot instead of connecting")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/recommendation/v3-tag-identity-20260925")
    args = parser.parse_args()
    source = json.loads(args.review.read_text(encoding="utf-8"))
    if args.snapshot:
        capture = json.loads(args.snapshot.read_text(encoding="utf-8"))
    else:
        from db_pool import validate_database_config
        config = validate_database_config()
        engine = create_engine(URL.create("mysql+pymysql", username=config["user"], password=config["password"],
            host=config["host"], port=config["port"], database=config["database"]),
            connect_args={"charset": "utf8mb4", "connect_timeout": 4, "read_timeout": 10})
        with engine.connect() as conn:
            conn.exec_driver_sql("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
            raw = snapshot(conn)
            # Only public catalog identity/tag data, never users or behavior.
            raw["websites"] = [{key: row.get(key) for key in ("id", "name", "url", "status", "source", "aliases")}
                               for row in raw["websites"]]
            tables = set(inspect(conn).get_table_names())
            capture = {"captured_at": datetime.now(timezone.utc).isoformat(), "database": config["database"],
                "alias_column_exists": "aliases" in {col["name"] for col in inspect(conn).get_columns("websites")},
                "stored_identity_or_redirect_tables": sorted(t for t in tables if "identity" in t or "alias" in t or "redirect" in t or t == "fetch_results"),
                "data": raw}
            conn.rollback()
        engine.dispose()
    data = capture["data"]
    report, mapped = resolve_review_queue(source, data)
    report["capture"] = {key: value for key, value in capture.items() if key != "data"}
    report["observed_causes"] = {
        "current_id_range": [min(row["id"] for row in data["websites"]), max(row["id"] for row in data["websites"])],
        "catalog_source_counts": dict(Counter(row.get("source") for row in data["websites"])),
        "old_approved_ids_present": sum(row["old_id_current_record"] is not None for row in report["rows"]),
        "operation_that_changed_ids": "unknown: no website history/merge/redirect ledger available; seed importer inserts missing URLs but does not prove which past operation replaced IDs",
        "conflict_reason_counts": dict(Counter(row["conflict_reason"] for row in report["rows"])),
    }
    plan = approved_tag_plan(mapped, data, source_queue=source)
    forward = {"version": MAPPING_VERSION, "command": "tags-preview", "database": capture["database"],
        "source_review_sha256": mapped["source_review_sha256"], "database_write_performed": False,
        "already_present": sum(row["already_present"] for row in plan),
        "pending": sum(not row["already_present"] for row in plan), "plan": plan}
    rollback = {"version": MAPPING_VERSION, "database_write_performed": False,
        "mode": "prospective_rollback_not_executable", "protect_existing_associations": True,
        "policy": "After test apply, generate executable rollback-preview from this version's journal; remove only owned link IDs, never tag dictionary or preexisting links.",
        "would_own": [{"site_id": row["site_id"], "tag": row["tag"]} for row in plan if not row["already_present"]]}
    for filename, document in [("catalog-snapshot.json", capture), ("mapping-preview.json", report),
        ("resolved-review.json", mapped), ("migration-preview.json", forward), ("rollback-preview.json", rollback)]:
        write_json(args.output_dir / filename, document)
    groups = defaultdict(list)
    for row in report["rows"]:
        if row["status"] == "unresolved":
            groups[(row["old"]["name"], row["old"]["url"], row["conflict_reason"])].append(row)
    lines = ["# 最小人工核对清单", "", "这些记录不在修订迁移中。不要按同名/同域名放行；不会自动恢复或新建缺失资源。", "",
             "| 原资源 | 旧 ID | 原 URL | 问题 | 最小待确认事项 |", "| --- | --- | --- | --- | --- |"]
    for (name, url, reason), records in groups.items():
        question = {"resource_missing": "确认是否应恢复独立资源；当前没有可迁移目标",
                    "different_product_path": "确认独立产品的目标 URL/记录；现有同域名其他路径不能替代",
                    "url_or_locale_changed": "确认是否保留独立语言/入口资源，并提供路径级身份依据"}.get(reason, "确认候选的名称、状态及完整 URL")
        lines.append(f"| {name} | {', '.join(str(r['old']['id']) for r in records)} | {url} | {reason} | {question} |")
    (args.output_dir / "manual-checklist.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
