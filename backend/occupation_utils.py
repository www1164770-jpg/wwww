"""Compatibility protocol for stable detailed career codes."""
from __future__ import annotations

from career_catalog import BY_CODE, LEGACY_CODE_MAP


OCCUPATION_LABELS = {code: item["name"] for code, item in BY_CODE.items()}

# Legacy aliases include the previously persisted codes and user-facing labels.
OCCUPATION_ALIASES = {
    **LEGACY_CODE_MAP,
    "programmer": "frontend_engineer", "frontend": "frontend_engineer",
    "backend": "backend_engineer", "product": "product_manager",
    "designer": "ui_ux_designer", "data": "data_analyst",
    "content_creator": "content_creator", "self_media_creator": "content_creator",
}

_OCCUPATION_LOOKUP = {code.casefold(): code for code in OCCUPATION_LABELS}
_OCCUPATION_LOOKUP.update({label.casefold(): code for code, label in OCCUPATION_LABELS.items()})
_OCCUPATION_LOOKUP.update({alias.casefold(): code for alias, code in OCCUPATION_ALIASES.items()})


def normalize_occupation(value):
    """Return a stable detailed career code, including legacy-code aliases."""
    key = str(value or "").strip().casefold()
    return _OCCUPATION_LOOKUP.get(key) if key else None


def get_occupation_label(value):
    canonical = normalize_occupation(value)
    return OCCUPATION_LABELS.get(canonical)
