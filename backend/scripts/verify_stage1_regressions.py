"""Capture focused existing tests without losing results in verbose fake-DB logs."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PATTERNS = ["test_resource_quality_stage1.py", "test_v3_tag_identity.py", "test_questionnaire_v*.py", "test_career*.py",
    "test_personalized_recommendation.py", "test_v3_tag_review_queue.py", "test_recommend_sort_v1.py",
    "test_favorites_v1.py", "test_auth.py", "test_ai_site_recommend_v1.py", "test_site_search_v1.py"]


def main():
    report = []
    for pattern in PATTERNS:
        command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", pattern]
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                             env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        output = run.stdout + run.stderr
        counts = re.findall(r"Ran (\d+) tests?", output)
        entry = {"pattern": pattern, "exit_code": run.returncode, "tests_run": int(counts[-1]) if counts else None,
                 "failures": re.findall(r"^FAIL: .+$", output, re.M), "errors": re.findall(r"^ERROR: .+$", output, re.M)}
        report.append(entry)
        print(json.dumps(entry))
    destination = ROOT / "docs/data/stage1-regression-results.json"
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(any(row["exit_code"] for row in report))


if __name__ == "__main__":
    raise SystemExit(main())
