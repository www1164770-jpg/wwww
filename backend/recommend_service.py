from datetime import datetime, timezone


# Stable questionnaire values are matched against site tags first, with text
# keywords retained as a fallback while the existing catalog is being enriched.
PROFILE_SIGNAL_KEYWORDS = {
    "frontend": ("frontend", "javascript", "typescript", "vue", "react", "css"),
    "backend": ("backend", "api", "server", "database", "python"),
    "fullstack": ("fullstack", "frontend", "backend", "api"),
    "mobile": ("mobile", "android", "ios", "flutter"),
    "ai_ml": ("ai", "machine learning", "model", "llm", "prompt"),
    "data": ("data", "sql", "analytics", "visualization"),
    "devops": ("devops", "deployment", "monitoring", "docker"),
    "ui_ux": ("ui", "ux", "design", "figma", "prototype"),
    "code_generation": ("code", "copilot", "cursor", "ai"),
    "debugging": ("debug", "bug", "error"),
    "ui_generation": ("ui", "design", "figma", "prototype"),
    "api_debugging": ("api", "postman", "http", "debug"),
    "documentation": ("docs", "documentation", "mdn"),
    "git_project_management": ("git", "github", "project"),
    "prototype": ("prototype", "figma", "axure"),
    "efficiency": ("efficiency", "office", "automation"),
    "easy_to_use": ("tutorial", "beginner"),
    "free_value": ("free",),
    "professional": ("professional", "enterprise"),
    "ai": ("ai", "assistant", "model"),
}

MATCH_WEIGHTS = {
    "occupation": 20,
    "direction": 30,
    "primary_need": 35,
    "priority": 10,
    "other_tags": 5,
}

SIGNAL_LABELS = {
    "frontend": "\u524d\u7aef\u5f00\u53d1\u65b9\u5411",
    "backend": "\u540e\u7aef\u5f00\u53d1\u65b9\u5411",
    "fullstack": "\u5168\u6808\u5f00\u53d1\u65b9\u5411",
    "mobile": "\u79fb\u52a8\u5f00\u53d1\u65b9\u5411",
    "ai_ml": "AI / \u673a\u5668\u5b66\u4e60\u65b9\u5411",
    "data": "\u6570\u636e\u5f00\u53d1\u65b9\u5411",
    "devops": "DevOps \u65b9\u5411",
    "ui_ux": "UI / UX \u65b9\u5411",
    "api_debugging": "API \u8c03\u8bd5\u9700\u6c42",
    "code_generation": "\u4ee3\u7801\u751f\u6210\u9700\u6c42",
    "ui_generation": "UI / \u9875\u9762\u751f\u6210\u9700\u6c42",
    "debugging": "\u4ee3\u7801\u8c03\u8bd5\u9700\u6c42",
    "documentation": "\u6280\u672f\u6587\u6863\u9700\u6c42",
    "git_project_management": "Git / \u9879\u76ee\u7ba1\u7406\u9700\u6c42",
    "free_value": "\u514d\u8d39\u4e0e\u6027\u4ef7\u6bd4\u504f\u597d",
    "ai": "AI \u80fd\u529b\u504f\u597d",
    "professional": "\u4e13\u4e1a\u6027\u504f\u597d",
    "efficiency": "\u6548\u7387\u504f\u597d",
    "easy_to_use": "\u6613\u4e0a\u624b\u504f\u597d",
}


def _to_number(value, default=0.0):
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _normalize_score(value, max_value=100.0):
    score = _to_number(value)
    if score > 1:
        return min(score / max_value, 1.0)
    return max(score, 0.0)


def _clean_list(value):
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _normalised_set(value):
    return {item.casefold() for item in _clean_list(value)}


def _site_text(site):
    parts = [
        site.get("name"),
        site.get("url"),
        site.get("summary"),
        site.get("description"),
        site.get("category_name"),
        " ".join(_clean_list(site.get("tags"))),
        " ".join(_clean_list(site.get("occupations"))),
    ]
    return " ".join(str(part or "") for part in parts).casefold()


def _signal_score(site_text, site_tags, signal):
    signal = str(signal or "").strip().casefold()
    if not signal:
        return 0.0
    if signal in site_tags:
        return 1.0
    keywords = PROFILE_SIGNAL_KEYWORDS.get(signal, ())
    if not keywords:
        return 0.0
    hits = sum(keyword.casefold() in site_text for keyword in keywords)
    return min(hits / max(len(keywords), 1), 1.0)


def _priority_score(site, site_text, site_tags, priority):
    priority = str(priority or "").strip().casefold()
    if not priority:
        return 0.0
    if priority == "free_value" and bool(site.get("is_free")):
        return 1.0
    if priority == "professional" and _normalize_score(site.get("quality_score")) >= 0.75:
        return 1.0
    if priority == "powerful" and (
        _normalize_score(site.get("quality_score")) >= 0.8
        or _to_number(site.get("recommend_level")) >= 8
    ):
        return 1.0
    return _signal_score(site_text, site_tags, priority)


def _is_blacklisted(site, rules):
    blacklist = _clean_list((rules or {}).get("blacklist"))
    return bool(blacklist) and any(
        keyword.casefold() in _site_text(site) for keyword in blacklist
    )


def _weights(rules):
    defaults = {
        "occupation_score": 0.4,
        "interest_score": 0.25,
        "quality_score": 0.2,
        "popularity_score": 0.1,
        "freshness_score": 0.05,
        "behavior_score": 0.05,
    }
    configured = (rules or {}).get("weights") or {}
    weights = {key: _to_number(configured.get(key), value) for key, value in defaults.items()}
    total = sum(value for value in weights.values() if value > 0)
    return defaults if total <= 0 else {key: max(value, 0.0) / total for key, value in weights.items()}


def _freshness_score(created_at):
    if not created_at:
        return 0.2
    try:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_days = max((datetime.now(timezone.utc) - created_at).days, 0)
    except Exception:
        return 0.2
    if age_days <= 7:
        return 1.0
    if age_days <= 30:
        return 0.7
    if age_days <= 90:
        return 0.4
    return 0.15


def score_site(site, user_profile=None, rules=None):
    user_profile = user_profile or {}
    rules = rules or {}
    occupation = str(user_profile.get("occupation") or "").strip().casefold()
    interests = _normalised_set(user_profile.get("interests"))
    site_occupations = _normalised_set(site.get("occupations"))
    site_tags = _normalised_set(site.get("tags"))
    site_text = _site_text(site)

    occupation_keywords = _normalised_set(
        (rules.get("occupation_site_weights") or {}).get(occupation)
    )
    occupation_score = 1.0 if occupation and (occupation in site_occupations or occupation in site_tags) else 0.0
    if "developer" in site_tags and occupation.endswith("_developer"):
        occupation_score = max(occupation_score, 0.6)
    if occupation_keywords:
        keyword_hits = sum(keyword in site_text for keyword in occupation_keywords)
        occupation_score = max(occupation_score, min(keyword_hits / len(occupation_keywords), 1.0))
    if not site_occupations and not site_tags:
        occupation_score = max(occupation_score, 0.3)

    direction_score = _signal_score(site_text, site_tags, user_profile.get("direction"))
    need_score = _signal_score(site_text, site_tags, user_profile.get("primary_need"))
    priority_score = _priority_score(site, site_text, site_tags, user_profile.get("priority"))
    reserved_signals = {
        str(user_profile.get(key) or "").casefold()
        for key in ("direction", "primary_need", "priority")
    }
    extra_tags = interests - reserved_signals
    other_tags_score = min(len(extra_tags & site_tags) / max(len(extra_tags), 1), 1.0) if extra_tags else 0.0
    has_adaptive_profile = any(user_profile.get(key) for key in ("direction", "primary_need", "priority"))

    quality_score = _normalize_score(site.get("quality_score"), 100.0)
    click_score = min(_to_number(site.get("click_count") or site.get("clicks")) / 1000.0, 1.0)
    favorite_score = min(_to_number(site.get("favorite_count")) / 200.0, 1.0)
    rating_score = min(_to_number(site.get("rating_avg")) / 5.0, 1.0)
    popularity_score = click_score * 0.45 + favorite_score * 0.35 + rating_score * 0.2
    freshness_score = _freshness_score(site.get("created_at"))
    behavior_score = _normalize_score(site.get("behavior_score"), 100.0)

    if has_adaptive_profile:
        score = (
            occupation_score * MATCH_WEIGHTS["occupation"]
            + direction_score * MATCH_WEIGHTS["direction"]
            + need_score * MATCH_WEIGHTS["primary_need"]
            + priority_score * MATCH_WEIGHTS["priority"]
            + other_tags_score * MATCH_WEIGHTS["other_tags"]
        )
    else:
        weights = _weights(rules)
        score = 100 * (
            occupation_score * weights["occupation_score"]
            + other_tags_score * weights["interest_score"]
            + quality_score * weights["quality_score"]
            + popularity_score * weights["popularity_score"]
            + freshness_score * weights["freshness_score"]
            + behavior_score * weights["behavior_score"]
        )

    reasons = []
    if occupation_score >= 0.5 and occupation:
        reasons.append("\u5339\u914d\u4f60\u7684\u804c\u4e1a\u5b9a\u4f4d")
    if direction_score > 0:
        reasons.append("\u7b26\u5408" + SIGNAL_LABELS.get(str(user_profile.get("direction") or ""), "\u7ec6\u5206\u65b9\u5411"))
    if need_score > 0:
        reasons.append("\u5339\u914d" + SIGNAL_LABELS.get(str(user_profile.get("primary_need") or ""), "\u6838\u5fc3\u9700\u6c42"))
    if priority_score > 0:
        reasons.append("\u7b26\u5408" + SIGNAL_LABELS.get(str(user_profile.get("priority") or ""), "\u5de5\u5177\u504f\u597d"))
    matched_tags = sorted(extra_tags & site_tags)
    if matched_tags:
        reasons.append("\u5173\u8054\u6807\u7b7e\uff1a" + "\u3001".join(matched_tags[:2]))
    if not reasons:
        reasons.append("\u4e0e\u4f60\u7684\u95ee\u5377\u753b\u50cf\u4fdd\u6301\u76f8\u5173")

    breakdown = {
        "occupation_score": round(occupation_score * 100, 2),
        "direction_score": round(direction_score * 100, 2),
        "need_score": round(need_score * 100, 2),
        "priority_score": round(priority_score * 100, 2),
        "other_tags_score": round(other_tags_score * 100, 2),
        "quality_score": round(quality_score * 100, 2),
        "popularity_score": round(popularity_score * 100, 2),
        "freshness_score": round(freshness_score * 100, 2),
        "behavior_score": round(behavior_score * 100, 2),
        "match_reasons": reasons[:4],
    }
    return round(min(score, 100), 2), reasons[0], breakdown


def rank_sites(sites, user_profile=None, limit=12, rules=None):
    scored = []
    for site in sites:
        if _is_blacklisted(site, rules):
            continue
        score, reason, breakdown = score_site(site, user_profile, rules)
        item = dict(site)
        item.setdefault("id", site.get("id"))
        item.setdefault("name", site.get("name"))
        item.setdefault("url", site.get("url"))
        item.setdefault("logo_url", site.get("logo_url"))
        item.setdefault("summary", site.get("summary") or site.get("description") or "")
        item.setdefault("tags", site.get("tags") or [])
        item.setdefault("occupations", site.get("occupations") or [])
        item["score"] = score
        item["match_score"] = score
        item["recommend_score"] = score
        item["match_reasons"] = breakdown.pop("match_reasons")
        item["reason"] = item.get("reason") or reason
        item["score_breakdown"] = breakdown
        item.update({key: value for key, value in breakdown.items() if key not in item})
        scored.append(item)
    scored.sort(
        key=lambda item: (
            _to_number(item.get("recommend_score")),
            _to_number(item.get("need_score")),
            _to_number(item.get("direction_score")),
            _to_number(item.get("quality_score")),
            _to_number(item.get("popularity_score")),
            str(item.get("name") or "").casefold(),
        ),
        reverse=True,
    )
    return scored[:limit]
