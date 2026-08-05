"""Questionnaire-driven career recommendation scoring."""

from __future__ import annotations

from collections import OrderedDict

from occupation_utils import get_occupation_label, normalize_occupation


PURPOSE_TAGS = {
    "efficiency": {"office efficiency", "automation", "product management"},
    "learning": {"learning platforms", "programming", "data analysis"},
    "ai_tools": {"AI tools", "programming", "model"},
    "project_development": {"programming", "project_development", "product management"},
    "design_assets": {"design resources", "assets", "AI tools"},
    "data_analysis": {"data analysis", "programming", "AI tools"},
    "content_creation": {"content_creation", "assets", "AI tools"},
    "industry_news": {"product management", "data analysis", "learning platforms"},
}

SKILL_LABELS = {
    "beginner": "入门能力",
    "junior": "初级能力",
    "intermediate": "中级能力",
    "senior": "高级能力",
}

SKILL_TAGS = {
    "beginner": {"入门能力", "学习成长"},
    "junior": {"初级能力", "项目实践"},
    "intermediate": {"中级能力", "项目实践"},
    "senior": {"高级能力", "复杂项目"},
}

PREFERENCE_TAGS = {
    "tutorial first": {"learning platforms", "tutorial"},
    "efficiency first": {"office efficiency", "automation"},
    "professional first": {"professional tools", "project management"},
    "free first": {"free tools"},
    "domestic first": {"domestic resources"},
    "international first": {"international resources"},
}


def _values(value):
    if isinstance(value, (list, tuple, set)):
        source = value
    elif value:
        source = str(value).split(",")
    else:
        source = []
    return [str(item).strip() for item in source if str(item).strip()]


def _lower_set(value):
    return {item.casefold() for item in _values(value)}


def _canonical_codes(occupations):
    codes = []
    for occupation in occupations or []:
        code = normalize_occupation(occupation)
        if code and code not in codes:
            codes.append(code)
    return codes


def _occupation_tags(code, occupation_tag_map):
    raw = (occupation_tag_map or {}).get(code) or []
    return {str(item).strip().casefold() for item in raw if str(item).strip()}


def filter_sites_for_career(sites, career_code, keywords=None):
    """Keep only resources associated with the requested career."""
    canonical_code = normalize_occupation(career_code)
    keyword_values = [str(item).strip().casefold() for item in (keywords or [])]
    matched = []
    for site in sites or []:
        occupations = _values(site.get("occupations"))
        exact_match = any(
            normalize_occupation(value) == canonical_code for value in occupations
        )
        searchable_text = " ".join(
            str(site.get(field) or "")
            for field in ("name", "summary", "description", "category_name")
        ).casefold()
        keyword_match = any(keyword in searchable_text for keyword in keyword_values)
        if exact_match or keyword_match:
            matched.append(site)
    return matched


def build_career_recommendations(profile, occupations, occupation_tag_map=None, limit=5):
    """Return ranked career cards from the latest questionnaire profile.

    The explicit occupation is one signal, not the complete result. Interests,
    purposes, skill level, and preferences all contribute to the score so an
    updated questionnaire can change both the ranking and the explanation.
    """
    profile = profile or {}
    codes = _canonical_codes(occupations)
    selected = normalize_occupation(profile.get("occupation"))
    interests = _lower_set(profile.get("interests"))
    purposes = _lower_set(profile.get("purposes"))
    preferences = _lower_set(profile.get("preferences"))
    purpose_tags = {
        tag.casefold()
        for purpose in purposes
        for tag in PURPOSE_TAGS.get(purpose, set())
    }
    skill_level = str(profile.get("skill_level") or "").strip().casefold()
    skill_tags = {tag.casefold() for tag in SKILL_TAGS.get(skill_level, set())}

    recommendations = []
    for code in codes:
        label = get_occupation_label(code) or code
        career_tags = _occupation_tags(code, occupation_tag_map)
        interest_matches = sorted(interests & career_tags)
        purpose_matches = sorted(purpose_tags & career_tags)
        preference_matches = sorted(preferences & career_tags)

        score = 20.0
        reasons = []
        if selected == code:
            score += 38
            reasons.append(f"你在问卷中选择了“{label}”方向")
        if interests:
            interest_score = 27 * len(interest_matches) / max(len(interests), 1)
            score += interest_score
            if interest_matches:
                reasons.append("兴趣标签匹配：" + "、".join(interest_matches[:3]))
        if purpose_matches:
            score += min(18, 8 * len(purpose_matches))
            reasons.append("使用目的与该方向相关")
        if skill_level:
            score += 7
            reasons.append(f"当前能力水平：{SKILL_LABELS.get(skill_level, skill_level)}")
        if preference_matches:
            score += min(5, len(preference_matches) * 2)
        if not reasons:
            reasons.append("根据问卷中的兴趣和使用目标综合匹配")

        recommendations.append(
            {
                "code": code,
                "label": label,
                "direction": _direction_for(code),
                "match_score": round(min(score, 99), 2),
                "reasons": reasons[:3],
                "reason": "；".join(reasons[:3]),
                "ability_tags": sorted(skill_tags) or [SKILL_LABELS.get(skill_level, "待补充能力水平")],
                "interest_tags": [*interest_matches, *purpose_matches][:6],
                "occupation_tags": sorted(career_tags),
            }
        )

    recommendations.sort(
        key=lambda item: (-item["match_score"], item["code"] == selected, item["code"])
    )
    return recommendations[: max(1, min(int(limit), len(recommendations))) ] if recommendations else []


def _direction_for(code):
    groups = OrderedDict(
        [
            ("技术研发", {"frontend_developer", "backend_developer", "ai_app_developer", "llm_engineer"}),
            ("产品与设计", {"product_manager", "ui_ux_designer"}),
            ("数据与运营", {"data_analyst", "operations", "technical_operations"}),
            ("教育与内容", {"student", "teacher", "creator"}),
        ]
    )
    return next((name for name, members in groups.items() if code in members), "通用方向")
