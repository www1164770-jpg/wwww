"""Validate and summarize the human review state without writing anything."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:  # Supports both ``python backend/scripts/...`` and package imports in tests.
    from .prepare_v3_tag_review_queue import validate_queue
except ImportError:  # pragma: no cover - direct script execution path
    from prepare_v3_tag_review_queue import validate_queue  # noqa: E402


def summarize(queue):
    items = list(queue.get("items") or [])
    errors = validate_queue(queue)
    statuses = ("approved", "rejected", "needs_review")
    by_status = {status: sum(item.get("review_status") == status for item in items) for status in statuses}
    by_signal = defaultdict(lambda: {"total": 0, "approved_records": 0, "rejected_records": 0, "needs_review": 0, "approved_tags": 0, "rejected_tags": 0})
    for item in items:
        row = by_signal[item.get("signal") or "unknown"]
        row["total"] += 1
        status = item.get("review_status")
        if status == "approved":
            row["approved_records"] += 1
        elif status == "rejected":
            row["rejected_records"] += 1
        elif status == "needs_review":
            row["needs_review"] += 1
        row["approved_tags"] += len(item.get("approved_tags") or [])
        row["rejected_tags"] += len(item.get("rejected_tags") or [])
    total = len(items)
    status_sum_ok = sum(by_status.values()) == total
    return {
        "phase": "V3_tag_phase_2.2-A",
        "mode": "human_review_summary",
        "total_candidates": total,
        "approved_records": by_status["approved"],
        "rejected_records": by_status["rejected"],
        "needs_review": by_status["needs_review"],
        "approved_tags_total": sum(len(item.get("approved_tags") or []) for item in items),
        "rejected_tags_total": sum(len(item.get("rejected_tags") or []) for item in items),
        "status_sum_ok": status_sum_ok,
        "validation_errors": errors,
        "ready_for_migration_preview": bool(total and status_sum_ok and not errors and by_status["needs_review"] == 0),
        "by_signal": dict(sorted(by_signal.items())),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Summarize V3 tag review status")
    parser.add_argument("review_queue", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    queue = json.loads(args.review_queue.read_text(encoding="utf-8"))
    summary = summarize(queue)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "total_candidates": summary["total_candidates"], "needs_review": summary["needs_review"], "ready_for_migration_preview": summary["ready_for_migration_preview"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
