"""Print a read-only description-quality report for catalog or database rows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from description_quality import analyze_records
from description_quality_sources import load_records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("catalog", "database"), default="database")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    parser.add_argument(
        "--restore-backup",
        type=Path,
        help="Reconstruct a pre-update report using an audit backup; never writes the database.",
    )
    args = parser.parse_args()
    records = load_records(args.source)
    if args.restore_backup:
        backup = json.loads(args.restore_backup.read_text(encoding="utf-8"))
        previous = {item["website_id"]: item.get("description") or "" for item in backup}
        records = [
            {**record, "description": previous.get(record.get("website_id"), record.get("description"))}
            for record in records
        ]
    report = {"source": args.source, **analyze_records(records)}
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
