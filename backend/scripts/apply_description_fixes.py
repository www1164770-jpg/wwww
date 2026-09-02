"""Apply only high-confidence website-description candidates with an audit.

The script never derives a stored description from a career, recommendation
reason, or category fallback.  Every update is guarded by its previous value,
so concurrent editorial changes are skipped rather than overwritten.
"""

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
from description_quality import build_candidate  # noqa: E402
from scripts.description_quality_sources import load_database_records  # noqa: E402


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def high_confidence_candidates() -> list[dict]:
    return [
        candidate
        for row in load_database_records()
        if (candidate := build_candidate(row)) and candidate["confidence"] == "high"
        and candidate["suggested_description"]
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persist the guarded high-confidence updates.")
    parser.add_argument(
        "--backup-output",
        type=Path,
        default=PROJECT_DIR / "docs" / "data" / "website-description-before-governance.json",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=PROJECT_DIR / "docs" / "data" / "website-description-governance-update-report.json",
    )
    args = parser.parse_args()

    candidates = high_confidence_candidates()
    backup = [
        {
            "website_id": item["website_id"],
            "name": item["name"],
            "url": item["url"],
            "description": item["current_description"],
        }
        for item in candidates
    ]
    if candidates or not args.backup_output.exists():
        write_json(args.backup_output, backup)

    updates: list[dict] = []
    skipped: list[dict] = []
    if args.apply:
        validate_database_config()
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                for item in candidates:
                    cursor.execute(
                        """
                        UPDATE websites
                        SET description=%s, summary=%s
                        WHERE id=%s
                          AND COALESCE(description, '')=%s
                          AND COALESCE(summary, '') IN ('', %s)
                        """,
                        (
                            item["suggested_description"],
                            item["suggested_description"],
                            item["website_id"],
                            item["current_description"],
                            item["current_description"],
                        ),
                    )
                    if cursor.rowcount == 1:
                        updates.append(item)
                    else:
                        skipped.append({**item, "reason": "record_changed_after_scan"})
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        updates = candidates

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if args.apply else "dry_run",
        "high_confidence_candidate_count": len(candidates),
        "updated_count": len(updates),
        "skipped_count": len(skipped),
        "updates": updates,
        "skipped": skipped,
    }
    write_json(args.report_output, payload)
    print(json.dumps({key: payload[key] for key in ("mode", "high_confidence_candidate_count", "updated_count", "skipped_count")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
