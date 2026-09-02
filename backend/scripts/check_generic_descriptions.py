"""Quality gate for active website descriptions.

The command fails when an active card can render without a description, when a
retired generic fallback remains, or when one description is shared by four or
more different website names.  Same-site duplicate records are reported but do
not fail this gate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from description_quality import analyze_records, description_without_name_prefix, is_generic_description  # noqa: E402
from description_language import analyze_description_languages  # noqa: E402
from scripts.description_quality_sources import load_database_records  # noqa: E402


def main() -> int:
    rows = load_database_records()
    generic_rows = [
        {
            "website_id": row["website_id"],
            "name": row["name"],
            "url": row["url"],
            "current_description": row.get("description") or "",
        }
        for row in rows
        if is_generic_description(description_without_name_prefix(row))
    ]
    empty_rows = [
        {
            "website_id": row["website_id"],
            "name": row["name"],
            "url": row["url"],
        }
        for row in rows
        if not str(row.get("description") or "").strip()
    ]
    report = analyze_records(rows)
    language_report = analyze_description_languages(rows)
    unrelated_duplicate_groups = [
        group for group in report["duplicate_groups"]
        if group["count"] >= 4 and len({site["name"] for site in group["websites"]}) >= 4
    ]
    payload = {
        "empty_description_count": len(empty_rows),
        "empty_rows": empty_rows,
        "generic_description_count": len(generic_rows),
        "generic_rows": generic_rows,
        "unrelated_duplicate_description_count": len(unrelated_duplicate_groups),
        "unrelated_duplicate_groups": unrelated_duplicate_groups,
        "language": language_report,
        **report,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not (empty_rows or generic_rows or unrelated_duplicate_groups or language_report["unsupported_language_descriptions"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
