"""Injected-session read queries and stable questionnaire serializers."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from questionnaire_models import (
    Occupation,
    QuestionnaireCondition,
    QuestionnaireDefinition,
    QuestionnaireOption,
    QuestionnaireQuestion,
    QuestionnaireVersion,
)


def _pagination(filters: dict) -> tuple[int, int]:
    """Return the page requested by a caller, with a safe service default."""
    page = int(filters.get("page", 1))
    page_size = int(filters.get("page_size", 20))
    if page < 1 or page_size < 1:
        raise ValueError("page and page_size must be positive")
    return page, page_size


def _page(
    session: Session,
    statement: Any,
    count_statement: Any,
    filters: dict,
    serializer: Any,
) -> dict:
    page, page_size = _pagination(filters)
    total = session.scalar(count_statement)
    records = session.scalars(
        statement.offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [serializer(record) for record in records],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


def _serialize_occupation(occupation: Occupation) -> dict:
    return {
        "id": occupation.id,
        "occupation_code": occupation.occupation_code,
        "name": occupation.name,
        "category": occupation.category,
        "sort_order": occupation.sort_order,
        "enabled": occupation.enabled,
        "new_occupation_policy": occupation.new_occupation_policy,
    }


def _definition_is_current_effective(definition: QuestionnaireDefinition) -> bool:
    return any(
        version.current_effective_scope_key is not None for version in definition.versions
    )


def _serialize_definition(definition: QuestionnaireDefinition) -> dict:
    occupation = definition.occupation
    return {
        "id": definition.id,
        "definition_code": definition.definition_code,
        "name": definition.name,
        "description": definition.description,
        "scope_type": definition.scope_type,
        "scope_key": definition.scope_key,
        "occupation_code": occupation.occupation_code if occupation is not None else None,
        "user_type": definition.user_type,
        "enabled": definition.enabled,
        "is_current_effective": _definition_is_current_effective(definition),
    }


def _serialize_version(version: QuestionnaireVersion) -> dict:
    return {
        "id": version.id,
        "definition_id": version.definition_id,
        "version_number": version.version_number,
        "status": version.status,
        "current_effective_scope_key": version.current_effective_scope_key,
        "is_current_effective": version.current_effective_scope_key is not None,
        "source_version_id": version.source_version_id,
        "version_description": version.version_description,
        "created_by_user_id": version.created_by_user_id,
        "published_by_user_id": version.published_by_user_id,
        "published_at": version.published_at,
    }


def _serialize_option(option: QuestionnaireOption) -> dict:
    return {
        "id": option.id,
        "option_value": option.option_value,
        "label": option.label,
        "sort_order": option.sort_order,
        "enabled": option.enabled,
    }


def _serialize_condition(condition: QuestionnaireCondition) -> dict:
    if (
        condition.source_question is None
        or condition.target_question is None
        or condition.expected_option is None
    ):
        raise ValueError("condition snapshot has missing relationships")
    return {
        "source_question_code": condition.source_question.question_code,
        "target_question_code": condition.target_question.question_code,
        "expected_option_value": condition.expected_option.option_value,
        "operator": condition.operator,
    }


def _serialize_question(question: QuestionnaireQuestion) -> dict:
    return {
        "id": question.id,
        "question_code": question.question_code,
        "title": question.title,
        "description": question.description,
        "question_type": question.question_type,
        "required": question.required,
        "sort_order": question.sort_order,
        "enabled": question.enabled,
        "is_general": question.is_general,
        "min_selections": question.min_selections,
        "max_selections": question.max_selections,
        "max_length": question.max_length,
        "option_values": [
            _serialize_option(option)
            for option in sorted(
                question.options, key=lambda option: (option.sort_order, option.option_value)
            )
        ],
        "condition": (
            _serialize_condition(question.target_condition)
            if question.target_condition is not None
            else None
        ),
    }


def list_occupations(session: Session, filters: dict) -> dict:
    """Return one stable, filtered page of occupation scopes."""
    statement = select(Occupation)
    count_statement = select(func.count()).select_from(Occupation)
    if "enabled" in filters:
        statement = statement.where(Occupation.enabled == filters["enabled"])
        count_statement = count_statement.where(Occupation.enabled == filters["enabled"])
    if "category" in filters:
        statement = statement.where(Occupation.category == filters["category"])
        count_statement = count_statement.where(Occupation.category == filters["category"])
    if "occupation_code" in filters:
        statement = statement.where(
            Occupation.occupation_code == filters["occupation_code"]
        )
        count_statement = count_statement.where(
            Occupation.occupation_code == filters["occupation_code"]
        )
    statement = statement.order_by(
        Occupation.sort_order, Occupation.occupation_code, Occupation.id
    )
    return _page(session, statement, count_statement, filters, _serialize_occupation)


def list_definitions(session: Session, filters: dict) -> dict:
    """Return one stable page of definitions and their current-effective state."""
    statement = select(QuestionnaireDefinition).options(
        selectinload(QuestionnaireDefinition.occupation),
        selectinload(QuestionnaireDefinition.versions),
    )
    count_statement = select(func.count()).select_from(QuestionnaireDefinition)
    if "scope_type" in filters:
        statement = statement.where(
            QuestionnaireDefinition.scope_type == filters["scope_type"]
        )
        count_statement = count_statement.where(
            QuestionnaireDefinition.scope_type == filters["scope_type"]
        )
    if "user_type" in filters:
        statement = statement.where(QuestionnaireDefinition.user_type == filters["user_type"])
        count_statement = count_statement.where(
            QuestionnaireDefinition.user_type == filters["user_type"]
        )
    if "enabled" in filters:
        statement = statement.where(QuestionnaireDefinition.enabled == filters["enabled"])
        count_statement = count_statement.where(
            QuestionnaireDefinition.enabled == filters["enabled"]
        )
    if "occupation_code" in filters:
        statement = statement.join(QuestionnaireDefinition.occupation).where(
            Occupation.occupation_code == filters["occupation_code"]
        )
        count_statement = count_statement.join(QuestionnaireDefinition.occupation).where(
            Occupation.occupation_code == filters["occupation_code"]
        )
    statement = statement.order_by(
        QuestionnaireDefinition.definition_code, QuestionnaireDefinition.id
    )
    return _page(session, statement, count_statement, filters, _serialize_definition)


def get_definition(session: Session, definition_id: int) -> dict | None:
    """Return one definition by primary key, or ``None`` when it is absent."""
    statement = (
        select(QuestionnaireDefinition)
        .where(QuestionnaireDefinition.id == definition_id)
        .options(
            selectinload(QuestionnaireDefinition.occupation),
            selectinload(QuestionnaireDefinition.versions),
        )
    )
    definition = session.scalar(statement)
    return _serialize_definition(definition) if definition is not None else None


def list_versions(session: Session, definition_id: int, filters: dict) -> dict:
    """Return one stable page of versions for the requested definition."""
    statement = select(QuestionnaireVersion).where(
        QuestionnaireVersion.definition_id == definition_id
    )
    count_statement = (
        select(func.count())
        .select_from(QuestionnaireVersion)
        .where(QuestionnaireVersion.definition_id == definition_id)
    )
    if "status" in filters:
        statement = statement.where(QuestionnaireVersion.status == filters["status"])
        count_statement = count_statement.where(
            QuestionnaireVersion.status == filters["status"]
        )
    if "current_effective" in filters:
        current_effective = filters["current_effective"]
        condition = (
            QuestionnaireVersion.current_effective_scope_key.is_not(None)
            if current_effective
            else QuestionnaireVersion.current_effective_scope_key.is_(None)
        )
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)
    statement = statement.order_by(
        QuestionnaireVersion.version_number, QuestionnaireVersion.id
    )
    return _page(session, statement, count_statement, filters, _serialize_version)


def get_version_snapshot(session: Session, version_id: int) -> dict | None:
    """Return a fully preloaded, stable-key snapshot for one version."""
    statement = (
        select(QuestionnaireVersion)
        .where(QuestionnaireVersion.id == version_id)
        .options(
            selectinload(QuestionnaireVersion.definition).joinedload(
                QuestionnaireDefinition.occupation
            ),
            selectinload(QuestionnaireVersion.questions)
            .options(
                selectinload(QuestionnaireQuestion.options),
                selectinload(QuestionnaireQuestion.target_condition).options(
                    joinedload(QuestionnaireCondition.source_question),
                    joinedload(QuestionnaireCondition.expected_option),
                ),
            ),
        )
    )
    version = session.scalar(statement)
    if version is None:
        return None

    snapshot = _serialize_version(version)
    definition = version.definition
    snapshot.update(
        {
            "definition_code": definition.definition_code,
            "definition_name": definition.name,
            "scope_key": definition.scope_key,
            "occupation_code": (
                definition.occupation.occupation_code
                if definition.occupation is not None
                else None
            ),
            "questions": [
                _serialize_question(question)
                for question in sorted(
                    version.questions,
                    key=lambda question: (question.sort_order, question.question_code),
                )
            ],
        }
    )
    return snapshot
