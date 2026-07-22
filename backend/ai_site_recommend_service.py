"""Deterministic local matching for the authenticated site recommendation endpoint."""

from __future__ import annotations

import html
import json
import math
import re
from urllib.parse import urlparse


_HTML_TAG_PATTERN = re.compile(r"<[^>]*>")
_UNSAFE_TEXT_PATTERN = re.compile(r"[^0-9a-z\u4e00-\u9fff+#._\-\s]")
_LIST_SEPARATOR_PATTERN = re.compile(r"[,，;；]")
_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")

_STOP_WORDS = {
    "一个", "一些", "用于", "可以", "需要", "帮我", "帮忙", "推荐", "网站", "工具", "平台",
    "the", "and", "for", "with", "that", "this", "from", "need", "want",
}

_TERM_GROUPS = (
    ("编程", "代码", "开发", "programming", "coding", "development"),
    ("调试", "debug", "debugging"),
    ("设计", "design", "designer"),
    ("数据分析", "数据", "分析", "data", "analytics", "analysis"),
    ("写作", "文案", "writing", "copywriting"),
    ("办公", "协作", "office", "collaboration"),
)


def _safe_string(value):
    if value is None:
        return ""
    try:
        return str(value)
    except Exception:
        return ""


def normalize_text(value):
    """Return a comparison-safe, lowercase representation of text."""
    value = html.unescape(_safe_string(value))
    value = _HTML_TAG_PATTERN.sub(" ", value).lower()
    value = _UNSAFE_TEXT_PATTERN.sub(" ", value)
    return " ".join(value.split())


def _clean_display_text(value):
    value = html.unescape(_safe_string(value))
    value = _HTML_TAG_PATTERN.sub(" ", value)
    return " ".join(value.split())


def normalize_string_list(value):
    """Convert JSON arrays, Python lists, and comma-separated text into strings."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = value
    elif isinstance(value, str):
        source = value.strip()
        if source.startswith("["):
            try:
                parsed = json.loads(source)
            except (TypeError, ValueError):
                parsed = None
            if isinstance(parsed, list):
                items = parsed
            else:
                items = _LIST_SEPARATOR_PATTERN.split(source)
        else:
            items = _LIST_SEPARATOR_PATTERN.split(source)
    else:
        items = [value]

    result = []
    for item in items:
        if isinstance(item, (list, tuple, set)):
            result.extend(normalize_string_list(item))
            continue
        cleaned = _clean_display_text(item)
        if cleaned:
            result.append(cleaned)
    return result


def _terms_for_query(query):
    terms = set()
    for word in re.findall(r"[a-z0-9][a-z0-9+#._-]*", query):
        if len(word) >= 2 and word not in _STOP_WORDS:
            terms.add(word)
    for group in re.findall(r"[\u4e00-\u9fff]{2,}", query):
        if group not in _STOP_WORDS:
            terms.add(group)
        if len(group) <= 8:
            terms.update(group[index:index + 2] for index in range(len(group) - 1))

    for group in _TERM_GROUPS:
        if any(alias in query for alias in group):
            terms.update(group)
    return sorted(term for term in terms if len(term) >= 2)


def _contains(value, term):
    return bool(value and term and term in value)


def _number(value):
    match = _NUMBER_PATTERN.search(_safe_string(value))
    if not match:
        return 0.0
    try:
        return float(match.group())
    except ValueError:
        return 0.0


def _clamp(value, lower, upper):
    return max(lower, min(upper, value))


def _valid_url(value):
    parsed = urlparse(_safe_string(value).strip())
    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)


def _id_number(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _first_match(terms, value):
    return next((term for term in terms if _contains(value, term)), "")


def _brief(value, maximum=24):
    value = _clean_display_text(value)
    return value[:maximum]


def _build_reason(evidence, occupation, interests):
    field, term, label = evidence
    term = _brief(term)
    label = _brief(label)
    occupation = _brief(occupation)
    if field == "name":
        return f"网站名称包含“{term}”，与本次需求直接相关。"
    if field == "tags":
        return f"网站标签包含“{term}”，与本次需求相符。"
    if field == "occupations":
        return f"网站适用职业包含“{term}”，与本次需求相符。"
    if field == "category":
        return f"网站属于“{label}”分类，与需求中的“{term}”相关。"
    if field == "summary":
        return f"网站摘要提到“{term}”，可支持本次需求。"
    if field == "description":
        return f"网站介绍提到“{term}”，与本次需求相关。"
    if field == "profile_occupation":
        return f"网站适用职业与当前“{occupation}”职业相符。"
    interest = _brief(interests[0]) if interests else term
    return f"网站标签与当前兴趣“{interest}”相符。"


def _score_candidate(candidate, query, terms, occupation, interests):
    name = normalize_text(candidate.get("name"))
    summary = normalize_text(candidate.get("summary"))
    description = normalize_text(candidate.get("description"))
    category = normalize_text(candidate.get("category_name"))
    tags = " ".join(normalize_text(item) for item in normalize_string_list(candidate.get("tags")))
    occupations = " ".join(normalize_text(item) for item in normalize_string_list(candidate.get("occupations")))

    scores = {"name": 0, "tags": 0, "occupations": 0, "category": 0, "summary": 0, "description": 0}
    evidence = []
    if query and _contains(name, query):
        scores["name"] += 12
        evidence.append(("name", query, ""))

    for term in terms:
        if _contains(name, term):
            scores["name"] += 8
            evidence.append(("name", term, ""))
        if _contains(tags, term):
            scores["tags"] += 7
            evidence.append(("tags", term, ""))
        if _contains(occupations, term):
            scores["occupations"] += 7
            evidence.append(("occupations", term, ""))
        if _contains(category, term):
            scores["category"] += 6
            evidence.append(("category", term, _clean_display_text(candidate.get("category_name"))))
        if _contains(summary, term):
            scores["summary"] += 4
            evidence.append(("summary", term, ""))
        if _contains(description, term):
            scores["description"] += 2
            evidence.append(("description", term, ""))

    field_score = sum(scores.values())
    if field_score <= 0:
        return None

    profile_score = 0
    normalized_occupation = normalize_text(occupation)
    cleaned_interests = normalize_string_list(interests)
    if normalized_occupation and _contains(occupations, normalized_occupation):
        profile_score += 5
        evidence.append(("profile_occupation", normalized_occupation, ""))
    for interest in cleaned_interests:
        normalized_interest = normalize_text(interest)
        if normalized_interest and (_contains(tags, normalized_interest) or _contains(category, normalized_interest)):
            profile_score += 3
            evidence.append(("interest", normalized_interest, ""))

    quality_score = _clamp(_number(candidate.get("quality_score")), 0, 100) / 100 * 2
    rating_score = _clamp(_number(candidate.get("rating_avg")), 0, 5) / 5
    favorites = max(0, _number(candidate.get("favorite_count")))
    clicks = max(0, _number(candidate.get("click_count", candidate.get("clicks", 0))))
    heat_score = min(math.log1p(favorites + clicks) / math.log1p(10000), 1) * 2
    total = field_score + profile_score + quality_score + rating_score + heat_score

    reason_order = ("name", "tags", "occupations", "category", "summary", "description", "profile_occupation", "interest")
    selected_evidence = next(
        (item for field in reason_order for item in evidence if item[0] == field),
        evidence[0],
    )
    return {
        "site": candidate,
        "score": round(total, 2),
        "text_score": field_score,
        "quality_score": quality_score,
        "favorite_count": favorites,
        "click_count": clicks,
        "reason": _build_reason(selected_evidence, _clean_display_text(occupation), cleaned_interests),
    }


def recommend_sites_for_query(query, candidates, occupation="", interests=None, limit=5):
    """Rank valid catalog candidates using only their stored metadata."""
    normalized_query = normalize_text(query)
    if len(normalized_query) < 2:
        return []
    terms = _terms_for_query(normalized_query)
    if not terms:
        return []
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 5
    limit = max(1, min(limit, 5))

    seen_ids = set()
    seen_urls = set()
    matched = []
    for index, candidate in enumerate(candidates or []):
        if not isinstance(candidate, dict):
            continue
        if normalize_text(candidate.get("status")) not in {"approved", "active"}:
            continue
        url = _safe_string(candidate.get("url")).strip()
        if not _valid_url(url):
            continue
        site_id = candidate.get("id")
        normalized_url = url.lower()
        if (site_id not in (None, "") and site_id in seen_ids) or normalized_url in seen_urls:
            continue
        if site_id not in (None, ""):
            seen_ids.add(site_id)
        seen_urls.add(normalized_url)
        scored = _score_candidate(candidate, normalized_query, terms, occupation, interests or [])
        if scored:
            scored["index"] = index
            matched.append(scored)

    matched.sort(
        key=lambda item: (
            -item["score"], -item["text_score"], -item["quality_score"],
            -item["favorite_count"], -item["click_count"], -_id_number(item["site"].get("id")), item["index"],
        )
    )
    for item in matched:
        item.pop("index", None)
    return matched[:limit]
