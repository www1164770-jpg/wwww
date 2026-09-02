"""Read-only coverage audit for Questionnaire V3 signals.

Usage:
    python backend/scripts/analyze_questionnaire_v3_signal_coverage.py
    python backend/scripts/analyze_questionnaire_v3_signal_coverage.py --output artifacts/v3-signal-coverage.json

The report never writes to MySQL. It only reads the current websites, tags,
site_tags, and site_occupations tables and reports exact token coverage.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db_pool import get_connection  # noqa: E402
from questionnaire_v3 import get_config  # noqa: E402


# A: high-signal recommendation tokens. B: preference/filter tokens. C:
# explanatory inputs that are intentionally mapped to a useful canonical token
# instead of becoming a raw website tag.
SIGNAL_GROUPS = {
    "A_direct_recommendation": {
        "developer_direction": {"frontend": ["frontend"], "backend": ["backend"], "fullstack": ["fullstack", "frontend", "backend"], "mobile": ["mobile"], "ai_ml": ["ai_ml", "ai"], "data": ["data"], "devops": ["devops"], "game": ["game"], "embedded": ["embedded"]},
        "tech_stack": {value: [value] for value in ("vue", "react", "angular", "javascript", "typescript", "html_css", "node", "python", "java", "go", "php", "csharp", "cpp", "pytorch", "tensorflow", "llm", "data_science", "docker", "kubernetes")},
        "primary_need": {value: [value] for value in ("code_generation", "debugging", "ui_generation", "api_debugging", "documentation", "git_project_management", "learning", "research", "homework", "ai_learning", "programming", "prototype", "ui_design", "copywriting", "script", "image_generation", "editing", "subtitle", "ai_video", "lesson_plan", "question_generation", "grading", "automation", "ai_office", "product_design", "analytics", "seo", "content", "ai_assistant", "efficiency", "content_creation", "data_processing", "ai")},
        "tasks": {value: [value] for value in ("new_features", "maintenance", "debugging", "api", "database", "testing", "code_review", "deployment", "research", "homework", "paper", "programming", "data_analysis", "prototype", "production", "copywriting", "editing", "subtitle", "lesson_plan", "resource_search", "documents", "spreadsheets", "automation", "analytics", "user_research", "seo", "content")},
        "content_platforms": {value: [value] for value in ("douyin", "bilibili", "xiaohongshu", "youtube", "wechat", "zhihu")},
        "designer_direction": {value: [value] for value in ("ui_ux", "graphic", "illustration", "branding", "3d", "motion")},
        "product_role": {value: [value] for value in ("product_manager", "product_operation", "user_operation", "content_operation", "marketing", "seo", "growth", "ecommerce")},
        "study_field": {value: [value] for value in ("computer_science", "engineering", "science", "business", "language", "humanities", "design", "medicine", "law", "education")},
    },
    "B_tool_preferences": {
        "priorities": {value: [value] for value in ("free_value", "chinese_support", "easy_to_use", "no_signup", "ai", "professional", "speed", "privacy", "cross_platform", "collaboration")},
        "platforms": {value: [value] for value in ("windows", "macos", "linux", "android", "ios", "web")},
        "budget_preference": {value: [value] for value in ("free_only", "free_first", "subscription_ok", "price_not_important")},
    },
    "C_explanatory_mappings": {
        "experience_level": {"beginner": ["beginner", "learning"], "basic": ["learning"], "intermediate": ["professional"], "advanced": ["professional"]},
        "pain_points": {"slow_coding": ["code_generation", "ai_coding"], "hard_debugging": ["debugging", "code_analysis"], "testing": ["testing", "code_generation"], "api_debugging": ["api_debugging", "api"], "documentation": ["documentation"], "project_management": ["project_management", "collaboration"], "deployment": ["deployment", "devops"], "learning_curve": ["learning"], "ai_code_quality": ["ai_coding", "code_analysis"]},
        "goals": {"efficiency": ["efficiency"], "learning": ["learning"], "ai_assistance": ["ai"], "automation": ["automation"], "content_creation": ["content_creation"], "data_processing": ["data", "analytics"], "collaboration": ["collaboration"], "project_management": ["project_management"], "research": ["research"], "professional_work": ["professional"]},
    },
}

IMPORTANCE_BY_SOURCE = {
    "primary_need": ("critical", 4), "developer_direction": ("high", 3),
    "tech_stack": ("high", 3), "designer_direction": ("high", 3),
    "product_role": ("high", 3), "content_platforms": ("high", 3),
    "study_field": ("medium", 2), "tasks": ("medium", 2),
    "pain_points": ("medium", 2), "goals": ("medium", 2),
    "experience_level": ("low", 1), "priorities": ("low", 1),
    "platforms": ("low", 1), "budget_preference": ("low", 1),
}


def _token(value):
    return str(value or "").strip().casefold()


def _read_catalog(connection):
    tags_by_site = defaultdict(set)
    occupations_by_site = defaultdict(set)
    with connection.cursor() as cursor:
        # Match the catalog's active population: approved rows plus legacy
        # rows whose status is NULL. Disabled entries are excluded, which is
        # why this currently aligns with the product's 946-site count.
        cursor.execute("SELECT id FROM websites WHERE status IS NULL OR status='approved'")
        website_ids = {int(row["id"]) for row in cursor.fetchall()}
        cursor.execute("SELECT st.site_id, t.name FROM site_tags st JOIN tags t ON t.id=st.tag_id")
        for row in cursor.fetchall():
            tags_by_site[int(row["site_id"])].add(_token(row.get("name")))
        # Site occupations are a first-class signal in this project and are
        # counted alongside tags for A-class role/direction coverage.
        cursor.execute("SELECT site_id, occupation FROM site_occupations")
        for row in cursor.fetchall():
            occupations_by_site[int(row["site_id"])].add(_token(row.get("occupation")))
    return website_ids, tags_by_site, occupations_by_site


def build_report(connection):
    website_ids, tags_by_site, occupations_by_site = _read_catalog(connection)
    total = len(website_ids)
    all_signals = []
    for group, sources in SIGNAL_GROUPS.items():
        for source, values in sources.items():
            for value, tokens in values.items():
                tag_matches = {site_id for site_id in website_ids if any(_token(token) in tags_by_site.get(site_id, set()) for token in tokens)}
                occupation_matches = {site_id for site_id in website_ids if any(_token(token) in occupations_by_site.get(site_id, set()) for token in tokens)}
                matching_sites = tag_matches | occupation_matches
                count = len(matching_sites)
                importance, importance_weight = IMPORTANCE_BY_SOURCE.get(source, ("medium", 2))
                all_signals.append({
                    "group": group, "source": source, "signal": value,
                    "tokens": tokens, "matched_sites": count,
                    "matched_by_tags": len(tag_matches),
                    "matched_by_occupations": len(occupation_matches),
                    "coverage_percent": round((count / total) * 100, 2) if total else 0,
                    "recommendation_importance": importance,
                    "importance_weight": importance_weight,
                    "status": "good" if count >= max(10, total * 0.05) else "low" if count else "none",
                })
    all_signals.sort(key=lambda item: (item["matched_sites"], item["group"], item["source"], item["signal"]))
    return {
        "questionnaire_version": 3,
        "profile_schema_version": 3,
        "algorithm_version": "phase1-v1",
        "website_count": total,
        "signal_count": len(all_signals),
        "signals": all_signals,
        "summary": {
            "none": sum(item["status"] == "none" for item in all_signals),
            "low": sum(item["status"] == "low" for item in all_signals),
            "good": sum(item["status"] == "good" for item in all_signals),
            "importance_weighted_coverage_percent": round(
                sum((item["coverage_percent"] / 100) * item["importance_weight"] for item in all_signals)
                / sum(item["importance_weight"] for item in all_signals) * 100, 2
            ) if all_signals else 0,
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit read-only V3 signal coverage")
    parser.add_argument("--output", type=Path, help="optional JSON output path")
    args = parser.parse_args(argv)
    connection = get_connection()
    try:
        report = build_report(connection)
    finally:
        connection.close()
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
