from datetime import datetime, timezone


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
    return " ".join(str(part or "") for part in parts).lower()


def _is_blacklisted(site, rules):
    blacklist = _clean_list((rules or {}).get("blacklist"))
    if not blacklist:
        return False
    text = _site_text(site)
    return any(keyword.lower() in text for keyword in blacklist)


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
    if total <= 0:
        return defaults
    return {key: max(value, 0.0) / total for key, value in weights.items()}


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
    occupation = user_profile.get("occupation") or ""
    interests = set(_clean_list(user_profile.get("interests")))

    site_occupations = set(_clean_list(site.get("occupations")))
    site_tags = set(_clean_list(site.get("tags")))
    occupation_keywords = set(
        _clean_list((rules.get("occupation_site_weights") or {}).get(occupation))
    )
    site_text = _site_text(site)

    occupation_score = 1.0 if occupation and occupation in site_occupations else 0.0
    if occupation_keywords:
        keyword_hits = sum(1 for keyword in occupation_keywords if keyword.lower() in site_text)
        occupation_score = max(
            occupation_score,
            min(keyword_hits / max(len(occupation_keywords), 1), 1.0),
        )
    if not site_occupations:
        occupation_score = max(occupation_score, 0.3)

    if interests and site_tags:
        interest_score = min(len(interests & site_tags) / max(len(interests), 1), 1.0)
    else:
        interest_score = 0.2

    quality_score = _normalize_score(site.get("quality_score"), 100.0)
    click_score = min(_to_number(site.get("click_count") or site.get("clicks")) / 1000.0, 1.0)
    favorite_score = min(_to_number(site.get("favorite_count")) / 200.0, 1.0)
    rating_score = min(_to_number(site.get("rating_avg")) / 5.0, 1.0)
    popularity_score = click_score * 0.45 + favorite_score * 0.35 + rating_score * 0.2
    freshness_score = _freshness_score(site.get("created_at"))
    behavior_score = _normalize_score(site.get("behavior_score"), 100.0)
    weights = _weights(rules)

    score = (
        occupation_score * weights["occupation_score"]
        + interest_score * weights["interest_score"]
        + quality_score * weights["quality_score"]
        + popularity_score * weights["popularity_score"]
        + freshness_score * weights["freshness_score"]
        + behavior_score * weights["behavior_score"]
    )

    reasons = []
    reason_templates = rules.get("reason_templates") or {}
    if occupation and reason_templates.get(occupation):
        reasons.append(reason_templates[occupation])
    elif occupation_score >= 1:
        reasons.append(f"适合 {occupation} 的资源使用场景")
    matched_tags = list(interests & site_tags)
    if matched_tags:
        reasons.append(f"因为你关注 {'、'.join(matched_tags[:2])}")
    if quality_score >= 0.75:
        reasons.append("资源质量评分较高")
    if popularity_score >= 0.5:
        reasons.append("近期用户收藏和访问较多")
    if freshness_score >= 0.7:
        reasons.append("近期更新或新收录资源")
    if not reasons:
        reasons.append(reason_templates.get("default") or "这是该分类下的高质量资源")

    breakdown = {
        "occupation_score": round(occupation_score * 100, 2),
        "interest_score": round(interest_score * 100, 2),
        "quality_score": round(quality_score * 100, 2),
        "popularity_score": round(popularity_score * 100, 2),
        "freshness_score": round(freshness_score * 100, 2),
        "behavior_score": round(behavior_score * 100, 2),
    }
    return round(score * 100, 2), reasons[0], breakdown


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
        item["recommend_score"] = score
        item["reason"] = item.get("reason") or reason
        item["score_breakdown"] = breakdown
        item.update({key: value for key, value in breakdown.items() if key not in item})
        scored.append(item)
    scored.sort(key=lambda item: item.get("recommend_score", 0), reverse=True)
    return scored[:limit]
