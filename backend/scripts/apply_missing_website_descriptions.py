"""Apply reviewed, high-confidence description candidates with a full audit."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db_pool import get_connection, validate_database_config  # noqa: E402


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--candidates", type=Path, default=PROJECT_DIR / "docs/data/missing-website-description-candidates.json")
    parser.add_argument("--backup-output", type=Path, default=PROJECT_DIR / "docs/data/website-descriptions-before-backfill.json")
    parser.add_argument("--report-output", type=Path, default=PROJECT_DIR / "docs/data/website-descriptions-backfill-report.json")
    parser.add_argument("--review-output", type=Path, default=PROJECT_DIR / "docs/data/website-description-review-queue.json")
    args = parser.parse_args()

    payload = json.loads(args.candidates.read_text(encoding="utf-8"))
    all_candidates = payload.get("candidates", [])
    candidates = [
        item for item in all_candidates
        if item.get("confidence") == "high" and str(item.get("suggested_description") or "").strip()
    ]
    review_queue = [item for item in all_candidates if item not in candidates]
    write_json(args.review_output, {"generated_at": datetime.now(timezone.utc).isoformat(), "count": len(review_queue), "items": review_queue})
    if not args.apply:
        print(json.dumps({"mode": "dry_run", "candidate_count": len(candidates), "needs_review": len(review_queue)}, ensure_ascii=False))
        return 0

    validate_database_config()
    conn = get_connection()
    backup, updates, skipped = [], [], []
    try:
        with conn.cursor() as cursor:
            for item in candidates:
                cursor.execute("SELECT description, summary FROM websites WHERE id=%s", (item["website_id"],))
                current = cursor.fetchone()
                if not current:
                    skipped.append({**item, "reason": "website_not_found"})
                    continue
                old_description = current.get("description") or ""
                old_summary = current.get("summary") or ""
                backup.append({"website_id": item["website_id"], "name": item["name"], "url": item["url"], "description": old_description, "summary": old_summary})
                cursor.execute(
                    "UPDATE websites SET description=%s, summary=%s WHERE id=%s AND COALESCE(description, '')=%s AND COALESCE(summary, '')=%s",
                    (item["suggested_description"].strip(), item["suggested_description"].strip(), item["website_id"], old_description, old_summary),
                )
                if cursor.rowcount == 1:
                    updates.append({**item, "old_description": old_description})
                else:
                    skipped.append({**item, "reason": "record_changed_during_apply"})
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    write_json(args.backup_output, backup)
    write_json(args.report_output, {
        "generated_at": datetime.now(timezone.utc).isoformat(), "mode": "apply",
        "candidate_count": len(candidates), "updated_count": len(updates), "skipped_count": len(skipped),
        "updates": updates, "skipped": skipped,
    })
    print(json.dumps({"mode": "apply", "candidate_count": len(candidates), "updated_count": len(updates), "skipped_count": len(skipped), "needs_review": len(review_queue)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
