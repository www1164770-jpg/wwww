"""Build auditable, website-specific description candidates from homepages.

The script only fetches a website's supplied homepage URL and reads public HTML
metadata.  It never follows login flows, executes JavaScript, or writes the
application database.  ``--fetch`` is opt-in so the same script can inspect an
existing candidate artifact without network access.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from description_quality import (  # noqa: E402
    build_candidate,
    clean_text,
    description_status,
    is_generic_description,
    REVIEWED_DESCRIPTION_OVERRIDES,
    SPECIFIC_DESCRIPTIONS,
)
from scripts.description_quality_sources import load_database_records  # noqa: E402


USER_AGENT = "ZhihuiDescriptionQualityBot/1.0 (+https://zhihui.local/description-quality)"
MAX_BYTES = 512_000
META_PATTERN = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
ATTRIBUTE_PATTERN = re.compile(
    r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>`]+))", re.IGNORECASE
)
TITLE_PATTERN = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _attributes(tag: str) -> dict[str, str]:
    return {
        name.lower(): html.unescape(quoted_double or quoted_single or bare or "")
        for name, quoted_double, quoted_single, bare in ATTRIBUTE_PATTERN.findall(tag)
    }


def extract_metadata(document: str) -> tuple[str, str]:
    description = ""
    for tag in META_PATTERN.findall(document):
        attributes = _attributes(tag)
        key = (attributes.get("name") or attributes.get("property") or "").lower()
        value = clean_text(attributes.get("content"))
        if key in {"description", "og:description", "twitter:description"} and value:
            description = value
            if key == "description":
                break
    title_match = TITLE_PATTERN.search(document)
    title = clean_text(html.unescape(title_match.group(1))) if title_match else ""
    return description, title


def compact_metadata_description(value: object, site_name: object, maximum: int = 90) -> str:
    """Keep a source-derived description readable in two card lines.

    Prefer a complete first sentence or clause.  This is trimming only: it
    never invents category wording or a synthetic fallback.
    """
    text = clean_text(value)
    name = clean_text(site_name)
    if name:
        text = re.sub(rf"^{re.escape(name)}\s*[:：\-|–—]\s*", "", text, flags=re.IGNORECASE)
    if len(text) <= maximum:
        return text
    sentence_ends = [match.end() for match in re.finditer(r"[。.!！？?]", text[: maximum + 1])]
    if sentence_ends and sentence_ends[-1] >= 20:
        return text[: sentence_ends[-1]].strip()
    clause_ends = [match.end() for match in re.finditer(r"[，,;；]", text[: maximum + 1])]
    if clause_ends and clause_ends[-1] >= 35:
        return text[: clause_ends[-1]].strip()
    return text[:maximum].rstrip("，,;；:：-–— ") + "…"


def fetch_homepage_metadata(record: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    url = str(record.get("url") or "").strip()
    if not url.startswith(("https://", "http://")):
        return {"metadata_description": "", "homepage_title": "", "fetch_error": "invalid_url"}
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "application/xhtml+xml"}:
                return {"metadata_description": "", "homepage_title": "", "fetch_error": f"content_type:{content_type}"}
            raw = response.read(MAX_BYTES)
            charset = response.headers.get_content_charset() or "utf-8"
            document = raw.decode(charset, errors="replace")
        description, title = extract_metadata(document)
        return {"metadata_description": description, "homepage_title": title, "fetch_error": ""}
    except HTTPError as exc:
        return {"metadata_description": "", "homepage_title": "", "fetch_error": f"http_{exc.code}"}
    except (URLError, TimeoutError, ValueError) as exc:
        return {"metadata_description": "", "homepage_title": "", "fetch_error": type(exc).__name__}


def candidate_from_record(record: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    base = build_candidate(record) or {}
    site_name = clean_text(record.get("name"))
    reviewed_description = clean_text(
        base.get("suggested_description") or SPECIFIC_DESCRIPTIONS.get(site_name)
    )
    if reviewed_description and (
        base.get("confidence") == "high" or site_name in REVIEWED_DESCRIPTION_OVERRIDES
    ):
        proposed = reviewed_description
        source = base.get("source") or "manual_verified"
        confidence = "high"
    else:
        proposed = clean_text(metadata.get("metadata_description"))
        source = "homepage_metadata" if proposed else ""
        confidence = "high" if proposed and 20 <= len(proposed) <= 180 and not is_generic_description(proposed) else "needs_review"
        proposed = compact_metadata_description(proposed, record.get("name")) if proposed else proposed
    if not proposed:
        proposed = clean_text(metadata.get("homepage_title"))
        source = "homepage_title" if proposed else "unavailable"
        confidence = "needs_review"
    return {
        "website_id": record.get("website_id"),
        "name": clean_text(record.get("name")),
        "url": clean_text(record.get("url")),
        "category": clean_text(record.get("category_name")),
        "tags": clean_text(record.get("tags")),
        "current_description": clean_text(record.get("description")),
        "suggested_description": proposed or None,
        "source": source,
        "confidence": confidence,
        "review_status": "ready_to_apply" if confidence == "high" else "needs_review",
        "quality_reason": base.get("reason") or description_status(record) or "duplicate_or_generic",
        "homepage_title": clean_text(metadata.get("homepage_title")),
        "fetch_error": metadata.get("fetch_error") or "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="Fetch public homepage metadata for quality candidates.")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--timeout", type=int, default=4)
    parser.add_argument(
        "--output", type=Path,
        default=PROJECT_DIR / "docs" / "data" / "missing-website-description-candidates.json",
    )
    args = parser.parse_args()
    records = [
        row for row in load_database_records()
        if description_status(row) is not None
        or is_generic_description(row.get("description"))
        or (
            clean_text(row.get("name")) in REVIEWED_DESCRIPTION_OVERRIDES
            and clean_text(row.get("description")) != SPECIFIC_DESCRIPTIONS.get(clean_text(row.get("name")), "")
        )
    ]
    metadata_by_id: dict[int, dict[str, Any]] = {}
    if args.fetch:
        with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 24))) as pool:
            futures = {
                pool.submit(fetch_homepage_metadata, row, max(1, args.timeout)): row
                for row in records
            }
            for future in as_completed(futures):
                row = futures[future]
                metadata_by_id[row["website_id"]] = future.result()
    candidates = [candidate_from_record(row, metadata_by_id.get(row["website_id"], {})) for row in records]
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "database_active_enabled_websites",
        "fetch_enabled": args.fetch,
        "candidate_count": len(candidates),
        "counts": {
            level: sum(item["confidence"] == level for item in candidates)
            for level in ("high", "medium", "needs_review")
        },
        "candidates": candidates,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("candidate_count", "counts", "fetch_enabled")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
