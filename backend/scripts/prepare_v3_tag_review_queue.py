"""Prepare a human-review queue from the read-only V3 candidate preview.

The generated queue is an approval artifact, not a migration. Every candidate
starts as ``needs_review`` and no database connection is opened by this tool.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ALLOWED_STATUSES = {"approved", "rejected", "needs_review"}
REVIEW_CHECK_KEYS = ("capability_confirmed", "tag_specific", "no_profile_pollution", "evidence_clear")


def prepare_queue(candidate_path: Path) -> dict:
    source = json.loads(candidate_path.read_text(encoding="utf-8"))
    items = []
    for candidate in source.get("candidates", []):
        items.append({
            "website": candidate.get("website"),
            "website_id": candidate.get("website_id"),
            "url": candidate.get("url"),
            "signal": candidate.get("signal"),
            "suggested_tags": list(candidate.get("suggested_tags") or []),
            "existing_tags": list(candidate.get("existing_tags") or []),
            "candidate_confidence": candidate.get("confidence", ""),
            "candidate_reason": candidate.get("reason", ""),
            "approved_tags": [],
            "rejected_tags": [],
            "review_status": "needs_review",
            "review_note": "",
            "review_checks": {
                "capability_confirmed": False,
                "tag_specific": False,
                "no_profile_pollution": False,
                "evidence_clear": False,
            },
        })
    return {
        "mode": "human_review_queue",
        "phase": "V3_tag_phase_2.2-A",
        "questionnaire_version": source.get("questionnaire_version", 3),
        "profile_schema_version": source.get("profile_schema_version", 3),
        "algorithm_version": source.get("algorithm_version", "phase1-v1"),
        "source_candidate_count": len(source.get("candidates", [])),
        "reviewed_count": 0,
        "approved_count": 0,
        "rejected_count": 0,
        "needs_review_count": len(items),
        "database_write_performed": False,
        "items": items,
    }


def validate_queue(queue: dict) -> list[str]:
    errors = []
    for index, item in enumerate(queue.get("items", [])):
        prefix = f"items[{index}]"
        status = item.get("review_status")
        if status not in ALLOWED_STATUSES:
            errors.append(f"{prefix}.review_status must be one of {sorted(ALLOWED_STATUSES)}")
        suggested = set(item.get("suggested_tags") or [])
        approved = set(item.get("approved_tags") or [])
        rejected = set(item.get("rejected_tags") or [])
        if not approved.issubset(suggested):
            errors.append(f"{prefix}.approved_tags must be a subset of suggested_tags")
        if not rejected.issubset(suggested):
            errors.append(f"{prefix}.rejected_tags must be a subset of suggested_tags")
        if approved & rejected:
            errors.append(f"{prefix} cannot approve and reject the same tag")
        checks = item.get("review_checks") or {}
        if status == "approved" and not all(checks.get(key) is True for key in REVIEW_CHECK_KEYS):
            errors.append(f"{prefix} approved requires all four review checks")
        if status == "approved" and not approved:
            errors.append(f"{prefix} approved requires at least one approved tag")
        if status == "rejected" and not rejected:
            errors.append(f"{prefix} rejected requires rejected_tags")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare a V3 tag review queue")
    parser.add_argument("candidate_json", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    queue = prepare_queue(args.candidate_json)
    errors = validate_queue(queue)
    if errors:
        raise SystemExit("Invalid generated queue: " + "; ".join(errors))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output), "items": len(queue["items"]),
        "review_status": "needs_review", "database_write_performed": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
