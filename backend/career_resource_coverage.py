"""Deterministic career-to-resource coverage for the website catalog.

The career catalog is intentionally broader than the questionnaire UI.  This
module makes that contract explicit: every career that can be returned by the
recommendation service is linked to a small, relevant set of real catalog
websites.  The links are persisted in ``site_occupations`` by the seed
importer, while the same rules provide a safe runtime fallback for databases
that have not yet been re-imported.
"""
from __future__ import annotations

from collections import defaultdict

from career_catalog import CAREERS, career_site_keywords, get_career


MIN_RESOURCES_PER_CAREER = 6

# Category-level relevance is deliberately conservative.  It is used only
# after career-specific tags, title and descriptions; it prevents a niche
# career from receiving an empty result while remaining in its real resource
# domain instead of falling back to arbitrary popular sites.
CATEGORY_RESOURCE_GROUPS = {
    "技术研发": {"docs", "community", "ui", "build_tools", "online_tools", "visualization_3d"},
    "人工智能": {"ai", "data", "docs", "build_tools"},
    "数据": {"data", "visualization_3d", "docs", "build_tools"},
    "设计": {"inspiration", "prototype", "ui", "assets", "fonts_colors", "online_tools"},
    "产品运营": {"prototype", "competitive_research", "office", "productivity", "data"},
    "内容": {"assets", "inspiration", "online_tools", "productivity", "learning"},
    "教育": {"learning", "docs", "data", "productivity"},
    "商务办公": {"office", "productivity", "data", "competitive_research"},
}

# These are existing catalog records, not frontend fixtures.  They guarantee
# that the most recognisable foundational tools lead the programming-learning
# result while the remaining positions continue to be ranked from metadata.
CAREER_PRIORITY_RESOURCES = {
    "programming_learner": (
        "GitHub", "MDN Web Docs", "freeCodeCamp", "LeetCode", "Stack Overflow",
    ),
}


def _text(site):
    values = (
        site.get("name"), site.get("url"), site.get("description"),
        site.get("summary"), site.get("category"), site.get("category_code"),
        " ".join(str(tag) for tag in site.get("tags") or ()),
    )
    return " ".join(str(value or "") for value in values).casefold()


def _score(career, site):
    text = _text(site)
    terms = career_site_keywords(career["code"])
    direct_hits = sum(term.casefold() in text for term in terms)
    category = str(site.get("category") or site.get("category_code") or "").casefold()
    category_match = category in CATEGORY_RESOURCE_GROUPS.get(career["category"], set())
    quality = float(site.get("quality_score") or 0)
    # Direct semantic evidence always outranks a category-only match.
    return direct_hits * 100 + (20 if category_match else 0) + quality / 100


def select_catalog_resources(career_code, sites, limit=MIN_RESOURCES_PER_CAREER):
    """Return real catalog records suitable for a detailed career code."""
    career = get_career(career_code)
    if not career:
        return []
    priorities = {
        name.casefold(): index
        for index, name in enumerate(CAREER_PRIORITY_RESOURCES.get(career["code"], ()))
    }
    ranked = sorted(
        (dict(site) for site in sites or []),
        key=lambda site: (
            str(site.get("name") or "").casefold() in priorities,
            -priorities.get(str(site.get("name") or "").casefold(), 0),
            _score(career, site),
            str(site.get("name") or "").casefold(),
        ),
        reverse=True,
    )
    return ranked[: max(1, int(limit or MIN_RESOURCES_PER_CAREER))]


def build_coverage_assignments(sites, minimum=MIN_RESOURCES_PER_CAREER):
    """Map each seed URL to the detailed career codes it supports.

    Raises when the source catalog cannot supply the promised minimum.  That
    turns a future career addition into an import/test failure instead of a
    user-facing empty state.
    """
    site_list = [site for site in sites or [] if site.get("url")]
    if len(site_list) < minimum:
        raise ValueError("website catalog is too small for career coverage")
    assignments = defaultdict(set)
    for career in CAREERS:
        selected = select_catalog_resources(career["code"], site_list, minimum)
        if len(selected) < minimum:
            raise ValueError(f"{career['code']} has insufficient resources")
        for site in selected:
            assignments[str(site["url"])].add(career["code"])
    return {url: tuple(sorted(codes)) for url, codes in assignments.items()}


def coverage_report(sites, minimum=MIN_RESOURCES_PER_CAREER):
    """Return a serializable, deterministic audit of career resource counts."""
    rows = []
    for career in CAREERS:
        resources = select_catalog_resources(career["code"], sites, minimum)
        rows.append({
            "code": career["code"], "name": career["name"],
            "resource_count": len(resources),
            "resources": [site.get("name") for site in resources],
        })
    return {"career_count": len(rows), "minimum": minimum, "careers": rows}
