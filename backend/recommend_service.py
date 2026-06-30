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


def score_site(site, user_profile=None):
    user_profile = user_profile or {}
    occupation = user_profile.get("occupation") or ""
    interests = set(user_profile.get("interests") or [])

    site_occupations = set(site.get("occupations") or [])
    site_tags = set(site.get("tags") or [])

    occupation_score = 1.0 if occupation and occupation in site_occupations else 0.0
    if not site_occupations:
        occupation_score = 0.3

    if interests and site_tags:
        interest_score = min(len(interests & site_tags) / max(len(interests), 1), 1.0)
    else:
        interest_score = 0.2

    quality_score = _normalize_score(site.get("quality_score"), 100.0)
    click_score = min(_to_number(site.get("click_count") or site.get("clicks")) / 1000.0, 1.0)
    favorite_score = min(_to_number(site.get("favorite_count")) / 200.0, 1.0)
    rating_score = min(_to_number(site.get("rating_avg")) / 5.0, 1.0)
    popularity_score = click_score * 0.45 + favorite_score * 0.35 + rating_score * 0.2
    freshness = _freshness_score(site.get("created_at"))

    score = (
        occupation_score * 0.4
        + interest_score * 0.25
        + quality_score * 0.2
        + popularity_score * 0.1
        + freshness * 0.05
    )

    reasons = []
    if occupation_score >= 1:
        reasons.append(f"Because your occupation is {occupation}")
    matched_tags = list(interests & site_tags)
    if matched_tags:
        reasons.append(f"Because you follow {', '.join(matched_tags[:2])}")
    if popularity_score >= 0.5:
        reasons.append("Recently popular among users")
    if not reasons:
        reasons.append("High quality resource in this category")

    return round(score * 100, 2), reasons[0]


def rank_sites(sites, user_profile=None, limit=12):
    scored = []
    for site in sites:
        score, reason = score_site(site, user_profile)
        item = dict(site)
        item["recommend_score"] = score
        item["reason"] = reason
        scored.append(item)
    scored.sort(key=lambda item: item.get("recommend_score", 0), reverse=True)
    return scored[:limit]
