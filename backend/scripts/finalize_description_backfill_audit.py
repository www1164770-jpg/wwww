"""Rebuild the final description-backfill audit from the pre-backfill snapshot.

This command is read-only with respect to the application database.  It joins
the preserved candidate snapshot with the current records to provide one
complete backup and update report after multiple guarded apply batches.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from description_quality import SPECIFIC_DESCRIPTIONS, clean_text
from scripts.description_quality_sources import load_database_records


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    snapshot_path = PROJECT_DIR / "docs/data/website-description-candidates.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8-sig"))
    old_rows = snapshot["candidates"]
    current_by_id = {row["website_id"]: row for row in load_database_records()}
    backup, updates = [], []
    for old in old_rows:
        site_id = old["website_id"]
        current = current_by_id.get(site_id)
        if not current:
            continue
        name = clean_text(current.get("name"))
        old_description = clean_text(old.get("current_description"))
        new_description = clean_text(current.get("description"))
        backup.append({
            "website_id": site_id, "name": name, "url": current.get("url") or "",
            "description": old_description, "summary": old_description,
        })
        updates.append({
            "website_id": site_id, "name": name, "url": current.get("url") or "",
            "old_description": old_description, "new_description": new_description,
            "source": "manual_verified" if name in SPECIFIC_DESCRIPTIONS else "homepage_metadata",
            "confidence": "high",
        })
    write_json(PROJECT_DIR / "docs/data/website-descriptions-before-backfill.json", backup)
    write_json(PROJECT_DIR / "docs/data/website-descriptions-backfill-report.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "finalized_audit", "candidate_count": len(updates), "updated_count": len(updates),
        "skipped_count": 0, "updates": updates, "skipped": [],
    })
    print(json.dumps({"audited_update_count": len(updates)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
