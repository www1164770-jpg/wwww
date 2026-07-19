"""Validation rules for questionnaire foundation records."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from questionnaire_constants import (
    NEW_OCCUPATION_POLICIES,
    QUESTIONNAIRE_SCOPE_TYPES,
    QUESTIONNAIRE_VERSION_STATUSES,
    USER_TYPES,
)

if TYPE_CHECKING:
    from questionnaire_models import (
        Occupation,
        QuestionnaireDefinition,
        QuestionnaireVersion,
    )


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


def build_scope_key(
    scope_type: str,
    occupation_code: str | None,
    user_type: str | None,
) -> str:
    """Build the one stable key used to match a definition's scope."""
    if scope_type not in QUESTIONNAIRE_SCOPE_TYPES:
        raise ValueError("invalid questionnaire scope_type")
    if scope_type == "general":
        if occupation_code is not None or user_type is not None:
            raise ValueError("general scope cannot include occupation or user type")
        return "general"
    if scope_type == "occupation":
        if (
            not isinstance(occupation_code, str)
            or not _OCCUPATION_CODE_RE.fullmatch(occupation_code)
            or user_type is not None
        ):
            raise ValueError("occupation scope requires only occupation_code")
        return f"occupation:{occupation_code}"
    if scope_type == "user_type":
        if occupation_code is not None or user_type not in USER_TYPES:
            raise ValueError("user_type scope requires a supported user type")
        return f"user_type:{user_type}"
    if (
        not isinstance(occupation_code, str)
        or not _OCCUPATION_CODE_RE.fullmatch(occupation_code)
        or user_type not in USER_TYPES
    ):
        raise ValueError("occupation_user_type scope requires both stable values")
    return f"occupation:{occupation_code}:user_type:{user_type}"


def validate_definition_scope(definition: "QuestionnaireDefinition") -> None:
    """Ensure the stored definition scope matches its supported dimensions."""
    occupation_code: str | None = None
    occupation = definition.occupation
    if definition.scope_type in {"occupation", "occupation_user_type"}:
        if occupation is None:
            raise ValueError("occupation scope requires an occupation")
        occupation_record_id = occupation.id
        if (
            definition.occupation_id is not None
            and (
                occupation_record_id is None
                or definition.occupation_id != occupation_record_id
            )
        ):
            raise ValueError("occupation relationship must match occupation_id")
        occupation_code = occupation.occupation_code
    elif definition.occupation_id is not None or occupation is not None:
        raise ValueError("this scope cannot include an occupation")

    expected_scope_key = build_scope_key(
        definition.scope_type,
        occupation_code,
        definition.user_type,
    )
    if definition.scope_key != expected_scope_key:
        raise ValueError("scope_key does not match definition scope")


def validate_version_state(
    version: "QuestionnaireVersion",
    definition: "QuestionnaireDefinition",
) -> None:
    """Validate the explicit current-effective state representation."""
    version_definition_id = version.definition_id
    if version_definition_id is None and version.definition is not None:
        version_definition_id = version.definition.id
    definition_id = definition.id
    if (version_definition_id is not None or definition_id is not None) and (
        version_definition_id != definition_id
    ):
        raise ValueError("version must be validated against its own definition")
    if (
        version_definition_id is None
        and definition_id is None
        and version.definition is not definition
    ):
        raise ValueError("version must be validated against its own definition")
    if not isinstance(version.version_number, int) or version.version_number < 1:
        raise ValueError("version_number must be at least one")
    if version.status not in QUESTIONNAIRE_VERSION_STATUSES:
        raise ValueError("invalid questionnaire version status")

    effective_key = version.current_effective_scope_key
    if effective_key is not None:
        if version.status != "published":
            raise ValueError("only published versions may have an effective scope key")
        if effective_key != definition.scope_key:
            raise ValueError("effective scope key must match definition scope")

    if version.status == "published" and (
        version.published_at is None or version.published_by_user_id is None
    ):
        raise ValueError("published versions require publisher and publication time")
    if version.published_at is not None and version.published_by_user_id is None:
        raise ValueError("publication time requires a publisher")


def validate_version_source(
    version: "QuestionnaireVersion",
    source_version: "QuestionnaireVersion | None",
) -> None:
    """Ensure a copied version references another version of its definition."""
    if source_version is None:
        return
    if source_version is version or (
        version.id is not None and source_version.id == version.id
    ):
        raise ValueError("a version cannot source itself")
    source_definition_id = source_version.definition_id
    if source_definition_id is None and source_version.definition is not None:
        source_definition_id = source_version.definition.id
    version_definition_id = version.definition_id
    if version_definition_id is None and version.definition is not None:
        version_definition_id = version.definition.id
    if (
        source_definition_id is not None or version_definition_id is not None
    ) and source_definition_id != version_definition_id:
        raise ValueError("source version must use the same definition")
    if (
        source_definition_id is None
        and version_definition_id is None
        and source_version.definition is not version.definition
    ):
        raise ValueError("source version must use the same definition")
