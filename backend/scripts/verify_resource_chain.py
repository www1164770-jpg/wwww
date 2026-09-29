"""Run actual Flask routes and MySQL writes in a fresh, isolated test schema.

Reads only schema definitions from the configured local catalog. Copies no users,
passwords, tokens, favorites or behavior. Leaves the test DB available for review.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import subprocess
from contextlib import nullcontext
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT), str(ROOT / "tests")]

import pymysql
from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import URL
from db_pool import validate_database_config
from v1_routes import register_v1_routes
from resource_migration import metadata, snapshot, approved_tag_plan, apply_plan, rollback_plan, rollback, maintenance_plan
from test_resource_quality_stage1 import RESEARCH, API


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create-isolated-test-db", action="store_true", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = validate_database_config()
    if config["host"] not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Integration runner only permits a local MySQL host")
    source = config["database"]
    target = "resource_chain_" + uuid4().hex[:12] + "_test"
    if not re.fullmatch(r"[a-zA-Z0-9_]+", source):
        raise ValueError("Unexpected source schema name")
    original = pymysql.connect(**config, cursorclass=pymysql.cursors.DictCursor)
    tables = ("users", "user_profiles", "websites", "categories", "tags", "site_tags", "site_occupations",
              "favorites", "comments", "user_behaviors", "user_questionnaire_responses")
    try:
        with original.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{target}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            for table in tables:
                cursor.execute("SELECT COUNT(*) AS n FROM information_schema.tables WHERE table_schema=%s AND table_name=%s", (source, table))
                if cursor.fetchone()["n"]:
                    cursor.execute(f"CREATE TABLE `{target}`.`{table}` LIKE `{source}`.`{table}`")
    finally:
        original.close()
    test_config = {**config, "database": target}
    def connect():
        return pymysql.connect(**test_config, cursorclass=pymysql.cursors.DictCursor)
    engine = create_engine("mysql+pymysql://", creator=lambda: pymysql.connect(**test_config))
    report = {"captured_at": datetime.now(timezone.utc).isoformat(), "test_database": target,
              "real_user_data_copied": False, "checks": []}
    def check(condition, description):
        if not condition:
            raise AssertionError(description)
        report["checks"].append(description)
    try:
        with connect() as conn, conn.cursor() as cursor:
            for name in ("research_fixture", "api_fixture", "empty_fixture", "v2_fixture"):
                cursor.execute("INSERT INTO users(username,email,password_hash,status) VALUES(%s,%s,%s,'active')",
                               (name, name + "@example.test", "not-a-real-login-hash"))
            cursor.execute("INSERT INTO categories(id,name) VALUES(1,'Test resources')")
            for sid, name, path, desc in [(1, "API Fixture", "API", "接口调试 HTTP API"),
                                           (2, "Literature Fixture", "Papers", "文献检索 scholarly literature research"),
                                           (3, "Unrelated Fixture", "Mail", "mail capital build")]:
                cursor.execute("INSERT INTO websites(id,name,url,category_id,summary,description,status) VALUES(%s,%s,%s,1,%s,%s,'approved')",
                               (sid, name, "https://example.test/" + path, desc, desc))
            for sid, tags in [(1, ["backend", "api", "python"]), (2, ["literature_search", "research", "paper"])]:
                for tag in tags:
                    cursor.execute("INSERT INTO tags(name,type) VALUES(%s,'general')", (tag,))
                    cursor.execute("INSERT INTO site_tags(site_id,tag_id) VALUES(%s,%s)", (sid, cursor.lastrowid))
            for sid, career in [(1, "api_engineer"), (1, "backend_engineer"), (2, "graduate_student")]:
                cursor.execute("INSERT INTO site_occupations(site_id,occupation,weight) VALUES(%s,%s,1)", (sid, career))
            conn.commit()
        app = Flask(__name__)
        app.config.update(TESTING=True, JWT_SECRET_KEY="resource-chain-fixture-only-secret-long-enough")
        JWTManager(app)
        register_v1_routes(app, connect)
        client = app.test_client()
        def headers(name):
            with app.app_context():
                return {"Authorization": "Bearer " + create_access_token(identity=name)}
        check(client.post("/api/questionnaire/submit", json={"version": 3, "answers": API}).status_code == 401,
              "Questionnaire rejects unauthenticated writes")
        for name, answers, expected in [("research_fixture", RESEARCH, 2), ("api_fixture", API, 1)]:
            auth = headers(name)
            response = client.post("/api/questionnaire/submit", json={"version": 3, "answers": answers}, headers=auth)
            check(response.status_code == 200, f"{name}: V3 questionnaire saved through real route")
            with connect() as conn, conn.cursor() as cursor:
                cursor.execute("SELECT r.profile_json FROM user_questionnaire_responses r JOIN users u ON u.id=r.user_id WHERE u.username=%s AND r.questionnaire_version=3", (name,))
                stored = json.loads(cursor.fetchone()["profile_json"])
            check(stored["primary_need"] == ("research" if expected == 2 else "api_debugging"), f"{name}: profile persisted in MySQL")
            if expected == 2:
                check("literature_search" in stored["detailed_needs"], "Research detail survives persistence")
            response = client.get("/api/career/recommendations", headers=auth)
            check(response.status_code == 200, f"{name}: career API succeeds")
            body = response.get_json()["data"]
            check(bool(body["careers"]) and body["websites"][0]["id"] == expected, f"{name}: distinct need ranks the matching website first")
            check(bool(body["websites"][0]["match_evidence"]), f"{name}: recommendation exposes actual matching fields")
            switched_ids = []
            for career in body["careers"][:2]:
                selected = client.get("/api/career/recommendations?career=" + career["code"], headers=auth).get_json()["data"]
                check(selected["selected_career"] == career["code"] and all(site["career_code"] == career["code"] for site in selected["websites"]), f"{name}: selected career {career['code']} refreshes matching response")
                switched_ids.append([site["id"] for site in selected["websites"]])
            check(len(switched_ids) == 2 and switched_ids[0] != switched_ids[1], f"{name}: career switch changes actual resource IDs, not just labels")
            check(len(body["websites"]) <= 3 and len({s["id"] for s in body["websites"]}) == len(body["websites"]), f"{name}: small candidate pool contains no fabricated/duplicate resources")
            fallback_response = client.get("/api/career/recommendations?career=" + body["careers"][1]["code"], headers=auth).get_json()["data"]
            unrelated = next(site for site in fallback_response["websites"] if site["id"] == 3)
            check(not unrelated["match_evidence"] and "暂无明确" in unrelated["reason"], f"{name}: unrelated fallback has neutral reason")
        empty = client.get("/api/career/recommendations", headers=headers("empty_fixture")).get_json()["data"]
        check(empty["websites"] == [] and not empty["questionnaire_completed"], "Empty profile returns questionnaire state and no fabricated careers")
        # Existing V2 data is a read fallback, not silently rewritten to V3.
        with connect() as conn, conn.cursor() as cursor:
            cursor.execute("INSERT INTO user_profiles(user_id,occupation,interests) SELECT id,'backend_engineer','[\"api\"]' FROM users WHERE username='v2_fixture'")
            cursor.execute("INSERT INTO user_questionnaire_responses(user_id,questionnaire_version,occupation,answers_json,profile_json) SELECT id,2,'developer','{}',%s FROM users WHERE username='v2_fixture'",
                (json.dumps({"profile_schema_version": 2, "occupation": "developer", "career_code": "backend_engineer", "direction": "backend", "primary_need": "api_debugging", "tags": ["api"]}),))
            conn.commit()
        v2 = client.get("/api/career/recommendations", headers=headers("v2_fixture")).get_json()["data"]
        check(v2["profile_version"] == "2" and v2["websites"][0]["id"] == 1, "V2 persisted profile remains compatible")
        auth = headers("api_fixture")
        favorite = client.post("/api/sites/1/favorite", json={"note": "isolated fixture"}, headers=auth)
        check(favorite.status_code == 200, "Authenticated favorite creation works")
        check(client.post("/api/sites/1/favorite", json={}, headers=auth).status_code == 200, "Duplicate favorite request remains idempotent")
        queue = {"items": [{"website_id": 1, "website": "API Fixture", "url": "https://example.test/API", "signal": "api_debugging",
            "suggested_tags": ["api_debugging", "developer_tools"], "approved_tags": ["api_debugging"], "rejected_tags": ["developer_tools"],
            "review_status": "approved", "candidate_reason": "synthetic fixture only", "review_note": "Synthetic test review",
            "review_checks": {k: True for k in ("capability_confirmed", "tag_specific", "no_profile_pollution", "evidence_clear")}}]}
        with engine.begin() as conn:
            metadata.create_all(conn)
        with engine.begin() as conn:
            plan = approved_tag_plan(queue, snapshot(conn))
            report["migration_preview"] = plan
            check(len(apply_plan(conn, plan)) == 1, "MySQL migration applies only approved tag subset")
        with engine.begin() as conn:
            check(apply_plan(conn, approved_tag_plan(queue, snapshot(conn))) == [], "Repeated MySQL migration creates no duplicate data")
            report["rollback_preview"] = rollback_plan(conn)
            rollback(conn)
            check(not rollback_plan(conn), "Rollback reverts only owned changes and is repeatable")
            check(conn.execute(text("SELECT COUNT(*) FROM favorites WHERE site_id=1")).scalar() == 1, "Favorite reference survives tag migration and rollback")
        base = {"kind": "field", "site_id": 1, "url": "https://example.test/API", "field": "summary", "source_ref": "synthetic fixture"}
        fields = [{**base, "value": "Human maintained fixture", "source_kind": "manual"},
                  {**base, "value": "Automated extraction", "source_kind": "web_extract"},
                  {**base, "value": "Unverified AI suggestion", "source_kind": "ai_suggestion"},
                  {"kind": "merge", "source_id": 1, "target_id": 2, "source_url": "https://example.test/API",
                   "target_url": "https://example.test/Papers", "reviewed": True, "evidence": "Synthetic equivalence for reference test only"}]
        with engine.begin() as conn:
            operations = maintenance_plan(fields, snapshot(conn))
            check(len(apply_plan(conn, operations)) == 4 and apply_plan(conn, operations) == [], "MySQL field and logical-merge operations are idempotent")
        detail = client.get("/api/sites/1", headers=auth).get_json()["data"]
        check(detail["summary"] == "Human maintained fixture" and detail["resource_metadata"]["summary"]["source_kind"] == "manual", "API retains human copy over web extraction and AI suggestions")
        check(detail["id"] == 1 and detail["canonical_site_id"] == 2 and detail["is_favorited"], "Logical merge exposes traceable identity while original favorite ID stays addressable")
        check(not detail["is_free_known"] and detail["pricing_model"] is None, "Unknown pricing remains unknown")
        with engine.begin() as conn:
            rollback(conn)
            check(conn.execute(text("SELECT COUNT(*) FROM websites")).scalar() == 3 and conn.execute(text("SELECT COUNT(*) FROM favorites")).scalar() == 1, "Maintenance rollback retains every website and favorite")
        response = client.get("/api/sites?page=1&page_size=1")
        page1 = response.get_json()["data"]
        page2 = client.get("/api/sites?page=2&page_size=1").get_json()["data"]
        check(response.status_code == 200 and len(page1["items"]) == 1 and page1["total"] == 3 and page1["items"][0]["id"] != page2["items"][0]["id"], "Website pagination returns distinct pages and accurate totals")
        # Exercise the public preview/apply CLI, including refusal without preview.
        with nullcontext(ROOT / "artifacts" / target) as temp:
            folder = Path(temp)
            folder.mkdir(parents=True, exist_ok=False)
            fixture = folder / "review.json"
            fixture.write_text(json.dumps(queue), encoding="utf-8")
            env = dict(os.environ, RESOURCE_TEST_DATABASE_URL=URL.create("mysql+pymysql", username=config["user"],
                password=config["password"], host=config["host"], port=config["port"], database=target,
                query={"charset": "utf8mb4"}).render_as_string(hide_password=False))
            def cli(command, output, preview=None):
                command_args = [sys.executable, str(ROOT / "backend/scripts/resource_quality.py"), command,
                    "--test-database", "--input", str(fixture), "--output", str(folder / output)]
                if preview:
                    command_args.extend(["--preview", str(folder / preview)])
                return subprocess.run(command_args, env=env, capture_output=True, text=True)
            check(cli("tags-apply", "blocked.json").returncode != 0, "CLI refuses writes without a prior preview")
            check(cli("tags-preview", "preview.json").returncode == 0 and cli("tags-apply", "apply.json", "preview.json").returncode == 0, "CLI preview and explicit test-database apply succeed")
            check(cli("tags-apply", "again.json", "preview.json").returncode == 0 and json.loads((folder / "again.json").read_text(encoding="utf-8"))["applied"] == [], "CLI repeated apply creates no duplicate associations")
            check(cli("rollback-preview", "rollback-preview.json").returncode == 0 and cli("rollback", "rollback.json", "rollback-preview.json").returncode == 0, "CLI rollback requires and consumes current rollback preview")
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["failure"] = type(error).__name__ + ": " + str(error)
        raise
    finally:
        engine.dispose()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        print(json.dumps({"test_database": target, "status": report.get("status"), "checks": len(report["checks"])}))


if __name__ == "__main__":
    main()
