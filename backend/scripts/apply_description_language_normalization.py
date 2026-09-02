"""Apply reviewed Chinese description rewrites with a backup and audit trail."""

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

from db_pool import get_connection, validate_database_config
from description_quality import LANGUAGE_NORMALIZATION_OVERRIDES, SPECIFIC_DESCRIPTIONS, clean_text
from scripts.description_quality_sources import load_database_records


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-output", type=Path, default=PROJECT_DIR / "docs/data/website-descriptions-before-language-normalization.json")
    parser.add_argument("--report-output", type=Path, default=PROJECT_DIR / "docs/data/website-description-language-normalization-report.json")
    args = parser.parse_args()
    candidates = [
        row for row in load_database_records()
        if clean_text(row.get("name")) in LANGUAGE_NORMALIZATION_OVERRIDES
        and clean_text(row.get("description")) != SPECIFIC_DESCRIPTIONS[clean_text(row.get("name"))]
    ]
    backup = [{"website_id": row["website_id"], "name": row["name"], "url": row["url"], "description": row.get("description") or "", "summary": row.get("summary") or ""} for row in candidates]
    updates, skipped = [], []
    if args.apply:
        validate_database_config(); conn = get_connection()
        try:
            with conn.cursor() as cursor:
                for row in candidates:
                    old_description, old_summary = row.get("description") or "", row.get("summary") or ""
                    new_description = SPECIFIC_DESCRIPTIONS[clean_text(row.get("name"))]
                    cursor.execute("UPDATE websites SET description=%s, summary=%s WHERE id=%s AND COALESCE(description,'')=%s AND COALESCE(summary,'')=%s", (new_description, new_description, row["website_id"], old_description, old_summary))
                    target = {"website_id": row["website_id"], "name": row["name"], "old_description": old_description, "new_description": new_description, "source": "manual_verified_language_normalization", "confidence": "high"}
                    (updates if cursor.rowcount == 1 else skipped).append(target)
            conn.commit()
        except Exception:
            conn.rollback(); raise
        finally:
            conn.close()
    write_json(args.backup_output, backup)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "mode": "apply" if args.apply else "dry_run", "candidate_count": len(candidates), "updated_count": len(updates), "skipped_count": len(skipped), "updates": updates, "skipped": skipped}
    write_json(args.report_output, report)
    print(json.dumps({key: report[key] for key in ("mode", "candidate_count", "updated_count", "skipped_count")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
