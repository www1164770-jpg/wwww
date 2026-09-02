"""Language policy for public website descriptions.

Chinese copy is preferred.  English brand names and technical terms are valid
inside Chinese copy, but scripts not supported by the product must never be
published as a formal description.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

ZH_RE = re.compile(r"[\u4e00-\u9fff]")
EN_RE = re.compile(r"[A-Za-z]")
UNSUPPORTED_SCRIPTS = {
    "japanese": re.compile(r"[\u3040-\u30ff\u31f0-\u31ff]"),
    "korean": re.compile(r"[\uac00-\ud7af\u1100-\u11ff]"),
    "russian": re.compile(r"[\u0400-\u052f]"),
    "arabic": re.compile(r"[\u0600-\u06ff\u0750-\u077f]"),
    "thai": re.compile(r"[\u0e00-\u0e7f]"),
}


def unsupported_languages(value: object) -> tuple[str, ...]:
    text = str(value or "")
    found = [name for name, pattern in UNSUPPORTED_SCRIPTS.items() if pattern.search(text)]
    # Reject other letter scripts too, while preserving Chinese, English and
    # ordinary punctuation/digits.  This prevents a new unsupported locale
    # from silently entering the formal data set.
    for char in text:
        if not char.isalpha() or ZH_RE.match(char) or EN_RE.match(char):
            continue
        if not any(pattern.match(char) for pattern in UNSUPPORTED_SCRIPTS.values()):
            found.append("other")
            break
    return tuple(found)


def description_language(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "empty"
    if unsupported_languages(text):
        return "unsupported"
    has_zh, has_en = bool(ZH_RE.search(text)), bool(EN_RE.search(text))
    if has_zh and has_en:
        return "zh_en"
    if has_zh:
        return "zh"
    if has_en:
        return "en"
    return "other"


def analyze_description_languages(records: Iterable[dict]) -> dict[str, object]:
    rows = list(records)
    classifications = Counter(description_language(row.get("description")) for row in rows)
    unsupported_rows = [
        {
            "website_id": row.get("website_id", row.get("id")),
            "name": row.get("name"), "url": row.get("url"),
            "description": row.get("description") or "",
            "languages": list(unsupported_languages(row.get("description"))),
        }
        for row in rows if description_language(row.get("description")) == "unsupported"
    ]
    unsupported_counts = Counter(
        language for row in unsupported_rows for language in row["languages"]
    )
    return {
        "total_websites": len(rows),
        "chinese_descriptions": classifications["zh"],
        "mixed_zh_en_descriptions": classifications["zh_en"],
        "english_descriptions": classifications["en"],
        "unsupported_language_descriptions": len(unsupported_rows),
        "unsupported_language_counts": dict(sorted(unsupported_counts.items())),
        "unsupported_rows": unsupported_rows,
        "empty_descriptions": classifications["empty"],
        "other_descriptions": classifications["other"],
    }
