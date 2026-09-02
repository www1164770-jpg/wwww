"""Generate a review-only JSON queue for website-description fixes.

This script has no SQL write path.  The resulting JSON must be reviewed before
any future publish workflow applies a description change.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from description_quality import build_candidate
from description_quality_sources import load_records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("catalog", "database"), default="database")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_DIR / "docs" / "data" / "website-description-fix-candidates.json",
    )
    args = parser.parse_args()
    candidates = [candidate for row in load_records(args.source) if (candidate := build_candidate(row))]
    counts = Counter(candidate["confidence"] for candidate in candidates)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": args.source,
        "write_policy": "review_only_no_database_writes",
        "counts": dict(sorted(counts.items())),
        "candidates": candidates,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "candidate_count": len(candidates), "counts": payload["counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
