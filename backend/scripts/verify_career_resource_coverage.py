"""Validate that every recommendable career has real seeded website resources."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from career_resource_coverage import MIN_RESOURCES_PER_CAREER, coverage_report  # noqa: E402


def load_sites():
    sites = []
    for path in sorted((BACKEND_DIR / "website_seed").glob("*.json")):
        sites.extend(json.loads(path.read_text(encoding="utf-8"))["sites"])
    return sites


def main():
    report = coverage_report(load_sites())
    failures = [row for row in report["careers"] if row["resource_count"] < MIN_RESOURCES_PER_CAREER]
    required = {"college_student", "programming_learner", "graduate_student", "researcher"}
    missing = required - {row["code"] for row in report["careers"]}
    programming = next(row for row in report["careers"] if row["code"] == "programming_learner")
    required_programming_resources = {"GitHub", "MDN Web Docs", "freeCodeCamp", "LeetCode", "Stack Overflow"}
    missing_programming_resources = required_programming_resources - set(programming["resources"])
    if failures or missing or missing_programming_resources:
        raise SystemExit(json.dumps({
            "failures": failures, "missing": sorted(missing),
            "missing_programming_resources": sorted(missing_programming_resources),
        }, ensure_ascii=False))
    print(json.dumps({
        "status": "PASS", "career_count": report["career_count"],
        "resources_per_career": MIN_RESOURCES_PER_CAREER,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
