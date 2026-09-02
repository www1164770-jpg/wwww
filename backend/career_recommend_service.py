"""Profile-based career ranking, intentionally separate from website ranking."""
from __future__ import annotations

from career_catalog import CAREERS, LEGACY_CODE_MAP, get_career


CAREER_MATCH_WEIGHTS = {
    "occupation": 15,
    "direction": 25,
    "primary_need": 20,
    "skills": 20,
    "tasks": 10,
    "pain_points": 5,
    "goals": 5,
}


def _values(value):
    if isinstance(value, (list, tuple, set)):
        source = value
    elif value:
        source = str(value).split(",")
    else:
        source = []
    return {str(item).strip().casefold() for item in source if str(item).strip()}


def _profile_values(profile, key, fallback=()):
    values = _values(profile.get(key))
    if not values and fallback:
        values = _values(profile.get("tags")) & set(fallback)
    return values


def _signal_score(values, strong, supporting, maximum):
    """Reward multiple direct signals without making one generic tag decisive."""
    strong = tuple(dict.fromkeys(strong))
    supporting = tuple(dict.fromkeys(supporting))
    strong_hits = values & set(strong)
    supporting_hits = values & set(supporting)
    if not strong_hits and not supporting_hits:
        return 0.0, []
    # Direct evidence counts twice as much as support.  A career with several
    # strong tags therefore outranks a loosely related specialty.
    denominator = max(2, min(4, len(strong) * 2 + len(supporting)))
    score = maximum * min(1.0, (len(strong_hits) * 2 + len(supporting_hits)) / denominator)
    return score, sorted(strong_hits | supporting_hits)


def _level(score):
    if score >= 80:
        return "very_high"
    if score >= 65:
        return "high"
    if score >= 50:
        return "medium"
    return "possible"


def _reason(text):
    return text


def _career_score(profile, career):
    occupation = str(profile.get("occupation") or "").strip().casefold()
    secondary_role = str(profile.get("secondary_role") or "").strip().casefold()
    direction = str(profile.get("direction") or "").strip().casefold()
    primary_need = str(profile.get("primary_need") or "").strip().casefold()
    skills = _profile_values(profile, "skills", career["strong_tags"] + career["supporting_tags"])
    tasks = _profile_values(profile, "tasks", career["tasks"])
    pains = _profile_values(profile, "pain_points", career["pain_points"])
    goals = _profile_values(profile, "goals", career["strong_tags"] + career["supporting_tags"])
    # V2 profile values remain usable as a weaker fallback when structured V3
    # fields do not exist.
    generic_tags = _values(profile.get("tags")) | _values(profile.get("interests"))
    # V3 tags are curated semantic evidence.  Add only catalog-relevant tags
    # to the skills evidence, so a captured ``database`` or ``deployment``
    # signal helps a related specialty without becoming a blanket boost.
    skills |= generic_tags & (set(career["strong_tags"]) | set(career["supporting_tags"]))
    if not skills:
        skills = generic_tags
    if not tasks:
        tasks = generic_tags
    if not pains:
        pains = generic_tags
    if not goals:
        goals = generic_tags

    score = 0.0
    reasons = {"identity": [], "direction": [], "need": [], "skills": [], "tasks": [], "pains": [], "goals": []}
    legacy_career = get_career(profile.get("career_code") or profile.get("occupation"))
    legacy_selected = legacy_career is career and occupation not in set(career["occupation"])
    if occupation in set(career["occupation"]) or secondary_role in set(career["occupation"]) or legacy_selected:
        score += CAREER_MATCH_WEIGHTS["occupation"]
        reasons["identity"].append(_reason("你的职业身份与该方向一致"))
    if legacy_selected:
        # V2 stored one coarse career code rather than the V3 evidence set.
        # Keep that explicit historic selection visible without treating it as
        # evidence for every sibling specialty.
        score += CAREER_MATCH_WEIGHTS["primary_need"]
    if direction and direction in set(career["directions"]):
        score += CAREER_MATCH_WEIGHTS["direction"]
        reasons["direction"].append(_reason(f"你的方向是 {direction}"))

    needs = {primary_need} if primary_need else set()
    need_score, need_hits = _signal_score(needs, career["strong_tags"] + career["tasks"], career["supporting_tags"], CAREER_MATCH_WEIGHTS["primary_need"])
    score += need_score
    if need_hits:
        reasons["need"].append(_reason("核心需求匹配：" + "、".join(need_hits[:2])))
    skill_score, skill_hits = _signal_score(skills, career["strong_tags"], career["supporting_tags"], CAREER_MATCH_WEIGHTS["skills"])
    score += skill_score
    if skill_hits:
        reasons["skills"].append(_reason("技能匹配：" + "、".join(skill_hits[:2])))
    task_score, task_hits = _signal_score(tasks, career["tasks"], career["supporting_tags"], CAREER_MATCH_WEIGHTS["tasks"])
    score += task_score
    if task_hits:
        reasons["tasks"].append(_reason("工作任务匹配：" + "、".join(task_hits[:2])))
    pain_score, pain_hits = _signal_score(pains, career["pain_points"], career["supporting_tags"], CAREER_MATCH_WEIGHTS["pain_points"])
    score += pain_score
    if pain_hits:
        reasons["pains"].append(_reason("当前难点匹配：" + "、".join(pain_hits[:2])))
    goal_score, goal_hits = _signal_score(goals, career["strong_tags"], career["supporting_tags"], CAREER_MATCH_WEIGHTS["goals"])
    score += goal_score
    if goal_hits:
        reasons["goals"].append(_reason("目标匹配：" + "、".join(goal_hits[:2])))

    # Keep explanations concise for the card while preserving meaningful
    # evidence.  No base score is added: unrelated jobs stay below threshold.
    core_reasons = [
        *reasons["skills"], *reasons["need"], *reasons["tasks"],
        *reasons["pains"], *reasons["goals"], *reasons["direction"], *reasons["identity"],
    ]
    return round(min(100, score), 2), core_reasons[:2]


def build_career_recommendations(profile, occupations=None, occupation_tag_map=None, limit=8):
    """Return up to eight explainable careers for V2 or V3 profiles.

    ``occupations`` and ``occupation_tag_map`` remain accepted for callers from
    the previous API, but the stable catalog is now the source of truth.
    """
    profile = dict(profile or {})
    legacy_code = profile.get("career_code") or profile.get("occupation")
    legacy_career = get_career(legacy_code)
    if legacy_career and not profile.get("career_code"):
        profile["career_code"] = legacy_career["code"]
    legacy_tags = []
    if occupation_tag_map and legacy_code:
        legacy_tags = (occupation_tag_map.get(str(legacy_code))
                       or occupation_tag_map.get(legacy_career["code"] if legacy_career else "")
                       or [])
    if legacy_tags:
        profile["tags"] = list(dict.fromkeys([*(profile.get("tags") or []), *legacy_tags]))
    rows = []
    for career in CAREERS:
        score, reasons = _career_score(profile, career)
        if score < 35:
            continue
        rows.append({
            "code": career["code"], "career_code": career["code"],
            "label": career["name"], "career_name": career["name"],
            "category": career["category"], "description": career["description"],
            "direction": career["category"], "match_score": score, "score": score,
            "match_level": _level(score), "match_reasons": reasons,
            "reasons": reasons, "reason": "；".join(reasons),
            "ability_tags": list(_values(profile.get("skills")) or _values(profile.get("skill_level")) or _values(profile.get("interests")))[:6],
            "occupation_tags": list(career["strong_tags"]),
            "interest_tags": list(career["supporting_tags"]),
        })
    rows.sort(key=lambda item: (-item["match_score"], item["code"]))
    return rows[: max(1, min(int(limit or 8), 8))]


def filter_sites_for_career(sites, career_code, keywords=None):
    """Compatibility helper used by older callers; matching uses stable code."""
    career = get_career(career_code)
    if not career:
        return []
    terms = {item.casefold() for item in (keywords or [])} | set(career["strong_tags"]) | set(career["supporting_tags"])
    matched = []
    for site in sites or []:
        haystack = " ".join(str(site.get(key) or "") for key in ("name", "summary", "description", "category_name"))
        haystack += " " + " ".join(str(item) for item in site.get("tags", []))
        if any(term in haystack.casefold() for term in terms):
            matched.append(site)
    return matched


__all__ = ["CAREER_MATCH_WEIGHTS", "LEGACY_CODE_MAP", "build_career_recommendations", "filter_sites_for_career"]
