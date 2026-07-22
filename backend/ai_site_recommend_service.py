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
    "我想", "我需要", "想找", "需要", "一个", "一些", "帮助", "帮我", "帮忙", "快速", "整理",
    "工作", "内容", "进行", "能够", "可以", "网站", "工具", "平台", "推荐", "资料", "制作", "生成",
    "the", "and", "for", "with", "that", "this", "from", "need", "want",
}

WEAK_TERMS = {"文档", "开发", "制作", "生成", "工作", "内容", "资料"}
EXPANDED_TERM_WEIGHT = 0.45

INTENT_TERM_GROUPS = {
    "programming_debug": {
        "explicit": (
            "python", "代码", "编程", "程序", "调试", "报错", "错误", "排错", "debug", "bug",
            "web", "框架文档", "开发文档", "框架", "api", "framework", "docs",
        ),
        "expanded": ("开发", "coding", "code", "编程", "调试", "debug", "programming", "debugging"),
    },
    "academic_writing": {
        "explicit": ("参考文献", "论文", "学术", "文献", "研究", "写作", "润色", "文章"),
        "expanded": ("学术研究", "论文写作", "文献检索", "writing"),
    },
    "image_design": {
        "explicit": ("生成图", "图片", "图像", "海报", "素材", "设计", "绘图", "视觉"),
        "expanded": ("原型设计", "素材资源", "design", "image"),
    },
    "translation": {
        "explicit": ("英译中", "中译英", "翻译", "英文", "中文", "语言", "translate", "translation"),
        "expanded": ("deepl", "中英文"),
    },
    "office_presentation": {
        "explicit": ("powerpoint", "演示文稿", "幻灯片", "ppt", "演示", "办公", "表格", "文档"),
        "expanded": ("文档办公", "presentation", "slides"),
    },
    "data_analysis": {
        "explicit": ("数据分析", "数据", "分析", "data", "analytics", "analysis"),
        "expanded": (),
    },
}

INTENT_CATEGORY_HINTS = {
    "programming_debug": {"开发社区", "编程开发"},
    "academic_writing": {"ai学术研究"},
    "image_design": {"素材资源", "原型设计"},
    "office_presentation": {"文档办公"},
}


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


def _query_term_matches(query):
    terms = {
        term
        for group in INTENT_TERM_GROUPS.values()
        for term in group["explicit"]
    }
    terms.update(
        word
        for word in re.findall(r"[a-z0-9][a-z0-9+#._-]*", query)
        if len(word) >= 2 and word not in _STOP_WORDS
    )
    matches = []
    for term in terms:
        start = query.find(term)
        if start >= 0:
            matches.append((start, -len(term), term))
    return sorted(matches)


def extract_query_terms(query):
    """Extract stable, controlled explicit and expanded terms from a query."""
    normalized_query = normalize_text(query)
    explicit = []
    occupied_ranges = []
    for start, negative_length, term in _query_term_matches(normalized_query):
        end = start - negative_length
        if any(start < occupied_end and end > occupied_start for occupied_start, occupied_end in occupied_ranges):
            continue
        occupied_ranges.append((start, end))
        explicit.append(term)

    intents = [
        intent
        for intent, group in INTENT_TERM_GROUPS.items()
        if set(explicit) & set(group["explicit"])
    ]
    expanded = []
    for intent in intents:
        for term in INTENT_TERM_GROUPS[intent]["expanded"]:
            if term not in explicit and term not in expanded:
                expanded.append(term)
    return {"explicit": explicit, "expanded": expanded, "intents": intents}


def _terms_for_query(query):
    term_data = extract_query_terms(query)
    return term_data["explicit"] + term_data["expanded"]


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


def _weak_term_matches_field(term, field, category, intents):
    if term == "文档":
        return field == "name" or (field == "category" and category == "文档办公")
    if term == "开发":
        return field == "category" and "programming_debug" in intents
    return False


def _score_candidate(candidate, query, term_data, occupation, interests):
    name = normalize_text(candidate.get("name"))
    summary = normalize_text(candidate.get("summary"))
    description = normalize_text(candidate.get("description"))
    category = normalize_text(candidate.get("category_name"))
    tags = " ".join(normalize_text(item) for item in normalize_string_list(candidate.get("tags")))
    occupations = " ".join(normalize_text(item) for item in normalize_string_list(candidate.get("occupations")))

    scores = {"name": 0, "tags": 0, "occupations": 0, "category": 0, "summary": 0, "description": 0}
    evidence = []
    explicit_terms = term_data["explicit"]
    expanded_terms = term_data["expanded"]
    intents = term_data["intents"]
    if query and explicit_terms == [query] and query not in WEAK_TERMS and _contains(name, query):
        scores["name"] += 12
        evidence.append(("name", query, ""))

    weighted_terms = [(term, 1) for term in explicit_terms]
    weighted_terms.extend((term, EXPANDED_TERM_WEIGHT) for term in expanded_terms)
    for term, multiplier in weighted_terms:
        if _contains(name, term):
            if term not in WEAK_TERMS or _weak_term_matches_field(term, "name", category, intents):
                scores["name"] += (12 if multiplier == 1 else 8 * multiplier)
                evidence.append(("name", term, ""))
        if _contains(tags, term):
            if term not in WEAK_TERMS or _weak_term_matches_field(term, "tags", category, intents):
                scores["tags"] += 7 * multiplier
                evidence.append(("tags", term, ""))
        if _contains(occupations, term):
            if term not in WEAK_TERMS or _weak_term_matches_field(term, "occupations", category, intents):
                scores["occupations"] += 7 * multiplier
                evidence.append(("occupations", term, ""))
        if _contains(category, term):
            if term not in WEAK_TERMS or _weak_term_matches_field(term, "category", category, intents):
                scores["category"] += 6 * multiplier
                evidence.append(("category", term, _clean_display_text(candidate.get("category_name"))))
        if _contains(summary, term):
            if term not in WEAK_TERMS or _weak_term_matches_field(term, "summary", category, intents):
                scores["summary"] += 4 * multiplier
                evidence.append(("summary", term, ""))
        if _contains(description, term):
            if term not in WEAK_TERMS or _weak_term_matches_field(term, "description", category, intents):
                scores["description"] += 2 * multiplier
                evidence.append(("description", term, ""))

    for intent in intents:
        if category in INTENT_CATEGORY_HINTS.get(intent, set()):
            scores["category"] += 3
            label = _clean_display_text(candidate.get("category_name"))
            evidence.append(("category", label, label))

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
    term_data = extract_query_terms(normalized_query)
    if not term_data["explicit"] and not term_data["expanded"]:
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
        scored = _score_candidate(candidate, normalized_query, term_data, occupation, interests or [])
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
