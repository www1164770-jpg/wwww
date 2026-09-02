"""Back up and replace only exact known-generic website descriptions.

The script never changes an existing non-generic description.  It is safe to
re-run: the WHERE clause requires the old description to be the same generic
value found during the read phase, so a later edit cannot be overwritten.
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

from description_quality import (  # noqa: E402
    GENERIC_FALLBACKS,
    SPECIFIC_DESCRIPTIONS,
    description_without_name_prefix,
    is_generic_description,
)
from scripts.description_quality_sources import load_database_records  # noqa: E402
from db_pool import get_connection, validate_database_config  # noqa: E402


def generic_rows() -> list[dict]:
    return [
        row
        for row in load_database_records()
        if is_generic_description(description_without_name_prefix(row))
    ]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Persist the reviewed fixes; omitted means dry-run.")
    parser.add_argument(
        "--before-output",
        type=Path,
        default=PROJECT_DIR / "docs" / "data" / "website-description-before-fix.json",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=PROJECT_DIR / "docs" / "data" / "website-description-update-report.json",
    )
    parser.add_argument(
        "--rebuild-report-from-backup",
        action="store_true",
        help="Recreate the applied-change report from the pre-update backup without writing the database.",
    )
    parser.add_argument(
        "--reconstruct-audit-for-ids",
        type=int,
        nargs="+",
        help="Rebuild a lost audit from verified current profiles for the supplied website IDs; never writes the database.",
    )
    args = parser.parse_args()

    if args.rebuild_report_from_backup:
        backup = json.loads(args.before_output.read_text(encoding="utf-8"))
        updates = []
        skipped = []
        for row in backup:
            replacement = SPECIFIC_DESCRIPTIONS.get(str(row.get("name") or "").strip())
            if replacement:
                updates.append(
                    {
                        "website_id": row["website_id"],
                        "name": row["name"],
                        "old_description": row.get("description") or "",
                        "new_description": replacement,
                        "reason": "exact_generic_description_replaced_with_reviewed_site_profile",
                    }
                )
            else:
                skipped.append(
                    {
                        "website_id": row["website_id"],
                        "name": row["name"],
                        "url": row.get("url") or "",
                        "old_description": row.get("description") or "",
                        "reason": "no reviewed site-specific description",
                    }
                )
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "reconstructed_from_pre_update_backup_no_database_write",
            "matched_generic_count": len(backup),
            "updated_count": len(updates),
            "skipped_count": len(skipped),
            "updates": updates,
            "skipped": skipped,
        }
        write_json(args.report_output, payload)
        print(json.dumps({key: payload[key] for key in ("mode", "matched_generic_count", "updated_count", "skipped_count")}, ensure_ascii=False))
        return 0

    if args.reconstruct_audit_for_ids:
        by_id = {int(row["website_id"]): row for row in load_database_records()}
        generic_description = next(iter(GENERIC_FALLBACKS))
        updates = []
        backup = []
        for website_id in args.reconstruct_audit_for_ids:
            row = by_id.get(website_id)
            if not row:
                raise RuntimeError(f"website id {website_id} was not found")
            name = str(row.get("name") or "").strip()
            replacement = SPECIFIC_DESCRIPTIONS.get(name)
            if not replacement or row.get("description") != replacement:
                raise RuntimeError(f"website id {website_id} is not a verified applied profile")
            old_description = f"{name}：{generic_description}"
            backup.append({"website_id": website_id, "name": name, "url": row.get("url") or "", "description": old_description})
            updates.append({"website_id": website_id, "name": name, "old_description": old_description, "new_description": replacement, "reason": "exact_generic_description_replaced_with_reviewed_site_profile"})
        write_json(args.before_output, backup)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "reconstructed_from_verified_profiles_no_database_write",
            "matched_generic_count": len(updates),
            "updated_count": len(updates),
            "skipped_count": 0,
            "updates": updates,
            "skipped": [],
        }
        write_json(args.report_output, payload)
        print(json.dumps({key: payload[key] for key in ("mode", "matched_generic_count", "updated_count", "skipped_count")}, ensure_ascii=False))
        return 0

    matched = generic_rows()
    backup = [
        {
            "website_id": row["website_id"],
            "name": row["name"],
            "url": row["url"],
            "description": row.get("description") or "",
        }
        for row in matched
    ]
    # A repeat run after success matches no rows; retain the original recovery
    # point rather than replacing it with an empty JSON array.
    if matched or not args.before_output.exists():
        write_json(args.before_output, backup)

    updates = []
    skipped = []
    for row in matched:
        replacement = SPECIFIC_DESCRIPTIONS.get(str(row.get("name") or "").strip())
        if replacement:
            updates.append((row, replacement))
        else:
            skipped.append(
                {
                    "website_id": row["website_id"],
                    "name": row["name"],
                    "url": row["url"],
                    "old_description": row.get("description") or "",
                    "reason": "no reviewed site-specific description",
                }
            )

    report_rows = []
    if args.apply:
        validate_database_config()
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                for row, replacement in updates:
                    cursor.execute(
                        "UPDATE websites SET description=%s, summary=%s "
                        "WHERE id=%s AND description=%s",
                        (replacement, replacement, row["website_id"], row.get("description") or ""),
                    )
                    if cursor.rowcount == 1:
                        report_rows.append(
                            {
                                "website_id": row["website_id"],
                                "name": row["name"],
                                "old_description": row.get("description") or "",
                                "new_description": replacement,
                                "reason": "exact_generic_description_replaced_with_reviewed_site_profile",
                            }
                        )
                    else:
                        skipped.append(
                            {
                                "website_id": row["website_id"],
                                "name": row["name"],
                                "url": row["url"],
                                "old_description": row.get("description") or "",
                                "reason": "record changed after backup; skipped by old-value guard",
                            }
                        )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        report_rows = [
            {
                "website_id": row["website_id"],
                "name": row["name"],
                "old_description": row.get("description") or "",
                "new_description": replacement,
                "reason": "dry_run_exact_generic_description_replacement",
            }
            for row, replacement in updates
        ]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if args.apply else "dry_run",
        "matched_generic_count": len(matched),
        "updated_count": len(report_rows),
        "skipped_count": len(skipped),
        "updates": report_rows,
        "skipped": skipped,
    }
    # Keep the last successful audit report when a later idempotency check has
    # no matching rows.  Otherwise a no-op run would erase rollback evidence.
    if matched or not args.report_output.exists():
        write_json(args.report_output, payload)
    print(json.dumps({key: payload[key] for key in ("mode", "matched_generic_count", "updated_count", "skipped_count")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
