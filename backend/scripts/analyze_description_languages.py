"""Report formal website-description languages for active websites."""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from description_language import analyze_description_languages
from scripts.description_quality_sources import load_database_records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT_DIR / "docs/data/website-description-language-report.json")
    args = parser.parse_args()
    report = analyze_description_languages(load_database_records())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in report if key != "unsupported_rows"}, ensure_ascii=False))
    return 0 if report["unsupported_language_descriptions"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
