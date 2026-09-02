"""Generate reviewed-before-write V3 tag candidates.

This command is intentionally read-only. It uses exact hostnames and explicit
website names only; it never searches for arbitrary substrings in URLs and it
never inserts or updates site_tags.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db_pool import get_connection  # noqa: E402


FIRST_BATCH = {
    "vue": {"tags": ["vue", "frontend"], "domains": ["vuejs.org"], "names": ["vue.js", "vue 官方文档"]},
    "react": {"tags": ["react", "frontend"], "domains": ["react.dev", "reactjs.org"], "names": ["react", "react 官方文档"]},
    "typescript": {"tags": ["typescript", "frontend"], "domains": ["typescriptlang.org"], "names": ["typescript", "typescript 官方文档"]},
    "javascript": {"tags": ["javascript", "frontend"], "domains": ["developer.mozilla.org"], "names": ["javascript", "mdn web docs", "mdn web 文档"]},
    "python": {"tags": ["python", "backend", "programming"], "domains": ["python.org", "docs.python.org"], "names": ["python", "python 官方文档"]},
    "java": {"tags": ["java", "backend", "programming"], "domains": ["dev.java", "openjdk.org"], "names": ["java", "java 官方文档"]},
    "go": {"tags": ["go", "backend", "programming"], "domains": ["go.dev", "golang.org"], "names": ["go", "golang"]},
    "node": {"tags": ["node", "javascript", "backend"], "domains": ["nodejs.org"], "names": ["node.js", "nodejs"]},
    "pytorch": {"tags": ["pytorch", "ai_ml", "python"], "domains": ["pytorch.org"], "names": ["pytorch"]},
    "tensorflow": {"tags": ["tensorflow", "ai_ml", "python"], "domains": ["tensorflow.org"], "names": ["tensorflow"]},
    "api_debugging": {"tags": ["api", "api_debugging", "testing", "developer_tools"], "domains": ["postman.com", "insomnia.rest", "swagger.io", "apidog.com"], "names": ["postman", "insomnia", "swagger", "apidog"]},
    "code_generation": {"tags": ["code_generation", "ai_coding", "developer_tools"], "domains": ["cursor.com", "codeium.com"], "names": ["github copilot", "cursor", "codeium", "replit"]},
    "debugging": {"tags": ["debugging", "code_analysis", "developer_tools"], "domains": ["sentry.io"], "names": ["sentry"]},
    "testing": {"tags": ["testing", "developer_tools"], "domains": ["playwright.dev", "cypress.io", "selenium.dev"], "names": ["playwright", "cypress", "selenium"]},
    "deployment": {"tags": ["deployment", "devops", "developer_tools"], "domains": ["vercel.com", "netlify.com", "render.com", "railway.app"], "names": ["vercel", "netlify", "render", "railway"]},
    "documentation": {"tags": ["documentation", "developer_tools"], "domains": ["readthedocs.io", "devdocs.io", "developer.mozilla.org"], "names": ["read the docs", "devdocs", "mdn web docs"]},
    "database": {"tags": ["database", "backend", "developer_tools"], "domains": ["mysql.com", "postgresql.org", "mongodb.com", "supabase.com", "redis.io"], "names": ["mysql", "postgresql", "postgres", "mongodb", "supabase", "redis"]},
    "git_project_management": {"tags": ["git_project_management", "collaboration", "developer_tools"], "domains": ["github.com", "gitlab.com", "bitbucket.org", "linear.app"], "names": ["github", "gitlab", "bitbucket", "linear"]},
}


def _norm(value):
    return " ".join(str(value or "").casefold().replace("_", " ").split())


def _host(url):
    host = (urlparse(str(url or "")).hostname or "").casefold().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def _domain_match(host, domains):
    return next((domain for domain in domains if host == domain or host.endswith("." + domain)), "")


def _load_sites(connection):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id,name,url,summary,description FROM websites WHERE status IS NULL OR status='approved'")
        sites = cursor.fetchall()
        cursor.execute("SELECT st.site_id,t.name FROM site_tags st JOIN tags t ON t.id=st.tag_id")
        tags = {}
        for row in cursor.fetchall():
            tags.setdefault(int(row["site_id"]), set()).add(_norm(row.get("name")))
    return sites, tags


def generate_candidates(connection):
    sites, site_tags = _load_sites(connection)
    candidates = []
    for site in sites:
        name = _norm(site.get("name"))
        host = _host(site.get("url"))
        for signal, rule in FIRST_BATCH.items():
            domain = _domain_match(host, rule["domains"])
            explicit_name = name if name in {_norm(item) for item in rule["names"]} else ""
            if not domain and not explicit_name:
                continue
            current = site_tags.get(int(site["id"]), set())
            missing = [tag for tag in rule["tags"] if _norm(tag) not in current]
            if not missing:
                continue
            candidates.append({
                "signal": signal, "website_id": int(site["id"]), "website": site.get("name"),
                "url": site.get("url"), "existing_tags": sorted(current),
                "suggested_tags": missing, "confidence": "high",
                "reason": f"exact_domain:{domain}" if domain else f"explicit_name:{explicit_name}",
            })
    candidates.sort(key=lambda item: (item["signal"], item["website"] or "", item["website_id"]))
    return {
        "questionnaire_version": 3, "profile_schema_version": 3,
        "algorithm_version": "phase1-v1", "mode": "preview_only",
        "write_performed": False, "signal_count": len(FIRST_BATCH),
        "candidate_count": len(candidates), "high_confidence_count": len(candidates),
        "candidates": candidates,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate high-confidence V3 tag candidates without writing")
    parser.add_argument("--output", type=Path, help="JSON preview path")
    parser.add_argument("--csv", dest="csv_path", type=Path, help="optional flat CSV preview path")
    args = parser.parse_args(argv)
    connection = get_connection()
    try:
        report = generate_candidates(connection)
    finally:
        connection.close()
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    if args.csv_path:
        args.csv_path.parent.mkdir(parents=True, exist_ok=True)
        with args.csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
            fields = ["signal", "website_id", "website", "url", "suggested_tags", "confidence", "reason"]
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for item in report["candidates"]:
                writer.writerow({**item, "suggested_tags": ",".join(item["suggested_tags"])})
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
