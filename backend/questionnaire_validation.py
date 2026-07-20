"""Validation rules for questionnaire foundation records."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Sequence

from questionnaire_constants import (
    CONDITION_OPERATORS,
    NEW_OCCUPATION_POLICIES,
    QUESTIONNAIRE_SCOPE_TYPES,
    QUESTIONNAIRE_VERSION_STATUSES,
    QUESTION_TYPES,
    USER_TYPES,
)

if TYPE_CHECKING:
    from questionnaire_models import (
        Occupation,
        QuestionnaireDefinition,
        QuestionnaireCondition,
        QuestionnaireOption,
        QuestionnaireQuestion,
        QuestionnaireVersion,
    )


_OCCUPATION_CODE_RE = re.compile(r"^[a-z0-9_]+$")


def _is_non_negative_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _validate_stable_code(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _OCCUPATION_CODE_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be lowercase and stable")


def _validate_non_empty_text(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must not be empty")


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
    relationship_definition_id = None
    if version.definition is not None:
        relationship_definition_id = version.definition.id
    if (
        version_definition_id is not None
        and relationship_definition_id is not None
        and version_definition_id != relationship_definition_id
    ):
        raise ValueError("version definition relationship must match definition_id")
    if version_definition_id is None:
        version_definition_id = relationship_definition_id
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
        if version.source_version_id is not None:
            raise ValueError("source_version_id requires a source version")
        return
    if version.source_version_id is not None and source_version.id != version.source_version_id:
        raise ValueError("source relationship must match source_version_id")
    if version.source_version_id is not None and version.id == version.source_version_id:
        raise ValueError("a version cannot source itself")
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


def validate_option(
    option: "QuestionnaireOption",
    question: "QuestionnaireQuestion | None" = None,
) -> None:
    """Validate option fields and, when known, its owning question relation."""
    _validate_stable_code(option.option_value, "option_value")
    _validate_non_empty_text(option.label, "option label")
    if not _is_non_negative_int(option.sort_order):
        raise ValueError("option sort_order must be non-negative")
    if not isinstance(option.enabled, bool):
        raise ValueError("option enabled must be a boolean")

    related_question = option.question
    _validate_relationship_key(
        option, "question_id", "question", "option question"
    )
    if question is not None and related_question is not None and related_question is not question:
        raise ValueError("option must be validated against its own question")
    expected_question = question if question is not None else related_question
    if (
        expected_question is not None
        and option.question_id is not None
        and expected_question.id is not None
        and option.question_id != expected_question.id
    ):
        raise ValueError("option question relationship must match question_id")


def validate_question(
    question: "QuestionnaireQuestion",
    options: Sequence["QuestionnaireOption"] | None = None,
) -> None:
    """Validate a question's stable fields and, when supplied, option constraints."""
    _validate_stable_code(question.question_code, "question_code")
    _validate_non_empty_text(question.title, "question title")
    if question.question_type not in QUESTION_TYPES:
        raise ValueError("invalid question_type")
    if not _is_non_negative_int(question.sort_order):
        raise ValueError("question sort_order must be non-negative")
    for value, field_name in (
        (question.required, "required"),
        (question.enabled, "enabled"),
        (question.is_general, "is_general"),
    ):
        if not isinstance(value, bool):
            raise ValueError(f"question {field_name} must be a boolean")

    _validate_relationship_key(
        question, "version_id", "version", "question version"
    )

    if question.question_type == "multiple_choice":
        _validate_multiple_choice_limits(question)
    elif question.question_type == "single_choice":
        if any(
            value is not None
            for value in (
                question.min_selections,
                question.max_selections,
                question.max_length,
            )
        ):
            raise ValueError("single_choice cannot define selection limits or max_length")
    else:
        if question.min_selections is not None or question.max_selections is not None:
            raise ValueError("short_text cannot define selection limits")
        if not isinstance(question.max_length, int) or isinstance(question.max_length, bool) or question.max_length <= 0:
            raise ValueError("short_text requires a positive max_length")

    if options is None:
        options = question.options
    validate_question_options(question, options)


def _validate_multiple_choice_limits(question: "QuestionnaireQuestion") -> None:
    minimum = question.min_selections
    maximum = question.max_selections
    if minimum is not None and not _is_non_negative_int(minimum):
        raise ValueError("multiple_choice min_selections must be non-negative")
    if maximum is not None and (
        not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0
    ):
        raise ValueError("multiple_choice max_selections must be positive")
    if question.required and (minimum is None or minimum < 1):
        raise ValueError("required multiple_choice requires a positive minimum")
    if minimum is not None and maximum is not None and maximum < minimum:
        raise ValueError("multiple_choice maximum cannot be less than minimum")
    if question.max_length is not None:
        raise ValueError("multiple_choice cannot define max_length")


def validate_question_options(
    question: "QuestionnaireQuestion",
    options: Sequence["QuestionnaireOption"],
) -> None:
    """Validate the supplied options as the complete option set for a question."""
    option_list = tuple(options)
    for option in option_list:
        validate_option(option, question)
    if question.question_type == "short_text":
        if option_list:
            raise ValueError("short_text cannot have options")
        return
    if not any(option.enabled for option in option_list):
        raise ValueError("choice questions require an enabled option")
    if question.question_type == "multiple_choice" and question.max_selections is not None:
        enabled_count = sum(option.enabled for option in option_list)
        if question.max_selections > enabled_count:
            raise ValueError("multiple_choice maximum exceeds enabled options")


def _related_id(record: object, id_attribute: str, relationship_attribute: str) -> object:
    record_id = getattr(record, id_attribute)
    if record_id is not None:
        return record_id
    related = getattr(record, relationship_attribute)
    return None if related is None else related.id


def _same_record(left: object, right: object) -> bool:
    left_id = getattr(left, "id")
    right_id = getattr(right, "id")
    if left_id is not None and right_id is not None:
        return left_id == right_id
    return left is right


def _version_key(record: object) -> object:
    version_id = getattr(record, "version_id")
    if version_id is not None:
        return ("id", version_id)
    version = getattr(record, "version")
    if version is None:
        return None
    if version.id is not None:
        return ("id", version.id)
    return ("transient", id(version))


def _validate_relationship_key(
    record: object,
    id_attribute: str,
    relationship_attribute: str,
    relationship_name: str,
    *,
    allow_transient_related: bool = False,
) -> None:
    foreign_key_id = getattr(record, id_attribute)
    related = getattr(record, relationship_attribute)
    if (
        foreign_key_id is not None
        and related is not None
        and (
            (related.id is None and not allow_transient_related)
            or (related.id is not None and foreign_key_id != related.id)
        )
    ):
        raise ValueError(f"{relationship_name} relationship must match its foreign key")


def validate_condition(
    source: "QuestionnaireQuestion",
    target: "QuestionnaireQuestion",
    expected_option: "QuestionnaireOption",
    operator: str,
) -> None:
    """Validate one condition against its source, target, and stable option."""
    _validate_relationship_key(
        source,
        "version_id",
        "version",
        "source question version",
        allow_transient_related=True,
    )
    _validate_relationship_key(
        target,
        "version_id",
        "version",
        "target question version",
        allow_transient_related=True,
    )
    _validate_relationship_key(
        expected_option,
        "question_id",
        "question",
        "condition option question",
        allow_transient_related=True,
    )
    source_version_id = _related_id(source, "version_id", "version")
    target_version_id = _related_id(target, "version_id", "version")
    if source_version_id is None and target_version_id is None:
        same_version = source.version is not None and source.version is target.version
    else:
        same_version = source_version_id == target_version_id
    if not same_version:
        raise ValueError("condition questions must belong to the same version")
    if _same_record(source, target):
        raise ValueError("condition cannot target its source question")
    if (
        not _is_non_negative_int(source.sort_order)
        or not _is_non_negative_int(target.sort_order)
        or source.sort_order >= target.sort_order
    ):
        raise ValueError("condition source must precede its target")
    option_question = expected_option.question
    if option_question is not None:
        option_belongs_to_source = _same_record(option_question, source)
    else:
        option_belongs_to_source = (
            expected_option.question_id is not None
            and source.id is not None
            and expected_option.question_id == source.id
        )
    if not option_belongs_to_source:
        raise ValueError("condition option must belong to its source question")
    if expected_option.enabled is not True:
        raise ValueError("condition option must be enabled")
    if operator not in CONDITION_OPERATORS:
        raise ValueError("invalid condition operator")
    if operator == "equals" and source.question_type != "single_choice":
        raise ValueError("equals conditions require a single_choice source")
    if operator == "contains" and source.question_type != "multiple_choice":
        raise ValueError("contains conditions require a multiple_choice source")


def validate_condition_graph(
    questions: Sequence["QuestionnaireQuestion"],
    conditions: Sequence["QuestionnaireCondition"],
) -> None:
    """Reject conditions outside the supplied version or forming a dependency cycle."""
    question_list = tuple(questions)
    condition_list = tuple(conditions)
    for question in question_list:
        _validate_relationship_key(
            question, "version_id", "version", "question version"
        )
    question_keys = {_question_key(question) for question in question_list}
    version_keys = {_version_key(question) for question in question_list}
    if len(version_keys) > 1:
        raise ValueError("condition graph questions must belong to one version")
    version_key = next(iter(version_keys), None)
    edges: dict[object, list[object]] = {key: [] for key in question_keys}
    target_keys: set[object] = set()
    for condition in condition_list:
        _validate_relationship_key(
            condition, "version_id", "version", "condition version"
        )
        _validate_relationship_key(
            condition,
            "source_question_id",
            "source_question",
            "condition source question",
        )
        _validate_relationship_key(
            condition,
            "target_question_id",
            "target_question",
            "condition target question",
        )
        _validate_relationship_key(
            condition,
            "expected_option_id",
            "expected_option",
            "condition expected option",
        )
        source = condition.source_question
        target = condition.target_question
        if source is None or target is None:
            raise ValueError("condition graph requires source and target questions")
        source_key = _question_key(source)
        target_key = _question_key(target)
        if source_key not in question_keys or target_key not in question_keys:
            raise ValueError("condition graph questions must be supplied")
        if _version_key(condition) != version_key:
            raise ValueError("condition must belong to the graph version")
        if target_key in target_keys:
            raise ValueError("condition graph allows only one condition per target")
        target_keys.add(target_key)
        edges[source_key].append(target_key)

    visiting: set[object] = set()
    visited: set[object] = set()

    def visit(question_key: object) -> None:
        if question_key in visiting:
            raise ValueError("condition graph cannot contain a cycle")
        if question_key in visited:
            return
        visiting.add(question_key)
        for target_key in edges[question_key]:
            visit(target_key)
        visiting.remove(question_key)
        visited.add(question_key)

    for question_key in question_keys:
        visit(question_key)
    for condition in condition_list:
        if condition.expected_option is None:
            raise ValueError("condition graph requires an expected option")
        validate_condition(
            condition.source_question,
            condition.target_question,
            condition.expected_option,
            condition.operator,
        )


def _question_key(question: "QuestionnaireQuestion") -> object:
    return question.id if question.id is not None else id(question)
