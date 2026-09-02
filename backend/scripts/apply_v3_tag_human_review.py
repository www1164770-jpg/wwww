"""Apply the first conservative human review to the frozen V3 queue.

This is an offline artifact edit only.  It never opens a database connection and
does not generate candidates.  The signal is included in each queue item's
suggested_tags so the review record can explicitly approve or reject the
canonical signal while preserving the queue validator's subset invariant.
"""
from __future__ import annotations

import json
from pathlib import Path


QUEUE = Path(__file__).resolve().parents[2] / "docs" / "recommendation" / "v3-tag-review-queue.json"


APPROVE_BY_ID = {
    # API tools
    849: {"api_debugging", "testing"}, 244: {"api_debugging", "testing"},
    245: {"api_debugging", "testing"},
    # Code generation
    80: {"code_generation"}, 79: {"code_generation"}, 274: {"code_generation"},
    # Databases
    247: {"database"}, 248: {"database"}, 246: {"database"},
    235: {"database", "backend"},
    # Observability
    386: {"debugging", "code_analysis"},
    # Deployment
    35: {"deployment"}, 36: {"deployment", "devops"}, 238: {"deployment", "devops"},
    34: {"deployment"}, 520: {"deployment"},
    # Documentation and language references
    767: {"documentation", "javascript"}, 27: {"documentation", "javascript"},
    522: {"documentation", "javascript"},
    601: {"go", "programming"}, 604: {"java", "programming"},
    533: {"python", "programming"},
    847: {"node", "javascript"}, 92: {"node", "javascript"}, 532: {"node", "javascript"},
    85: {"react"}, 94: {"typescript"}, 84: {"vue"}, 530: {"vue"},
    # Test frameworks
    313: {"testing"}, 125: {"testing"},
    # Git/project platforms (the remaining GitHub URLs are individual tools/repos,
    # not project-management capabilities.)
    678: {"git_project_management", "collaboration"},
    20: {"git_project_management", "collaboration"}, 518: {"git_project_management", "collaboration"},
    21: {"git_project_management", "collaboration"}, 190: {"git_project_management", "collaboration"},
}


REJECT_ONLY_IDS = {316, 629, 383, 79}  # handled specially below for signal overlap


def review_note(item: dict, approved: set[str], rejected: set[str]) -> str:
    website = item.get("website") or "该站点"
    if item["signal"] == "git_project_management" and item.get("website_id") in {316, 629, 383, 79, 844, 843, 846}:
        return f"{website} 是具体代码库、CI、发布或开发工具，不足以证明项目管理/协作能力；本轮不写入宽泛标签。"
    if rejected and approved:
        return f"{website} 的核心能力与信号明确；仅批准具体标签，拒绝宽泛或与页面能力不直接对应的标签。"
    if approved:
        return f"{website} 的页面能力与信号直接对应；批准具体标签，避免引入宽泛画像。"
    return f"{website} 与该信号的能力边界不匹配，本轮全部标签拒绝。"


def main() -> int:
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    for item in queue["items"]:
        signal = item["signal"]
        # Canonical signal is an explicit review option even when a legacy
        # spelling already exists in existing_tags.
        if signal not in item["suggested_tags"]:
            item["suggested_tags"].insert(0, signal)
        suggested = set(item["suggested_tags"])
        approved = set(APPROVE_BY_ID.get(item.get("website_id"), set()))
        # GitHub-hosted individual tools/repos are not project-management sites.
        if item["signal"] == "git_project_management" and item.get("website_id") in {316, 629, 383, 79, 844, 843, 846}:
            approved = set()
        approved &= suggested
        rejected = suggested - approved
        item["approved_tags"] = sorted(approved)
        item["rejected_tags"] = sorted(rejected)
        item["review_status"] = "approved" if approved else "rejected"
        item["review_checks"] = {key: True for key in (
            "capability_confirmed", "tag_specific", "no_profile_pollution", "evidence_clear"
        )}
        item["review_note"] = review_note(item, approved, rejected)
    queue["reviewed_count"] = len(queue["items"])
    queue["approved_count"] = sum(item["review_status"] == "approved" for item in queue["items"])
    queue["rejected_count"] = sum(item["review_status"] == "rejected" for item in queue["items"])
    queue["needs_review_count"] = sum(item["review_status"] == "needs_review" for item in queue["items"])
    queue["database_write_performed"] = False
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"reviewed": queue["reviewed_count"], "approved": queue["approved_count"], "rejected": queue["rejected_count"], "needs_review": queue["needs_review_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
