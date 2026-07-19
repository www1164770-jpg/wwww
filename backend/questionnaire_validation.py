"""Validation rules for questionnaire foundation records."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from questionnaire_constants import NEW_OCCUPATION_POLICIES

if TYPE_CHECKING:
    from questionnaire_models import Occupation


_OCCUPATION_CODE_RE = re.compile(r"^[a-z0-9_]+$")


def validate_occupation(occupation: "Occupation") -> None:
    """Reject occupation values that cannot serve as stable scope identifiers."""
    if not isinstance(occupation.occupation_code, str) or not _OCCUPATION_CODE_RE.fullmatch(
        occupation.occupation_code
    ):
        raise ValueError("occupation_code must be lowercase and stable")
    if not isinstance(occupation.name, str) or not occupation.name.strip():
        raise ValueError("occupation name must not be empty")
    if not isinstance(occupation.sort_order, int) or occupation.sort_order < 0:
        raise ValueError("occupation sort_order must be non-negative")
    if occupation.new_occupation_policy not in NEW_OCCUPATION_POLICIES:
        raise ValueError("invalid new_occupation_policy")
