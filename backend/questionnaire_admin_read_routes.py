"""Read-only administrator routes for the questionnaire foundation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from flask import Flask, request
from werkzeug.exceptions import MethodNotAllowed, NotFound

from models import db
from questionnaire_admin_support import (
    QuestionnaireParameterError,
    optional_boolean,
    optional_text,
    pagination_filters,
    questionnaire_admin_required,
    questionnaire_error,
    questionnaire_response,
)
from questionnaire_read_service import (
    get_definition,
    get_version_snapshot,
    list_definitions,
    list_occupations,
    list_versions,
)


QUESTIONNAIRE_ADMIN_READ_PREFIX = "/api/admin/questionnaires"


def _is_questionnaire_admin_read_path(path: str) -> bool:
    return path == QUESTIONNAIRE_ADMIN_READ_PREFIX or path.startswith(
        f"{QUESTIONNAIRE_ADMIN_READ_PREFIX}/"
    )


def _filters(*names: str) -> dict[str, Any]:
    filters: dict[str, Any] = pagination_filters()
    for name in names:
        value = optional_boolean(name) if name in ("enabled", "current_effective") else optional_text(name)
        if value is not None:
            filters[name] = value
    return filters


def register_questionnaire_admin_read_routes(
    app: Flask,
    get_db_connection: Callable[[], Any],
) -> None:
    """Register only the Task 8 occupation and definition GET endpoints."""

    required = questionnaire_admin_required(get_db_connection)

    @app.before_request
    def questionnaire_admin_read_routing_error():
        routing_exception = request.routing_exception
        if not _is_questionnaire_admin_read_path(request.path):
            return None
        if isinstance(routing_exception, NotFound):
            return questionnaire_error("not found", code=404)
        if isinstance(routing_exception, MethodNotAllowed):
            response, status = questionnaire_error("method not allowed", code=405)
            for header, value in routing_exception.get_headers():
                if header.lower() == "allow":
                    response.headers[header] = value
            return response, status
        return None

    @app.get("/api/admin/questionnaires/occupations")
    @required
    def questionnaire_admin_occupations():
        try:
            filters = _filters("enabled", "category", "occupation_code")
            return questionnaire_response(list_occupations(db.session, filters))
        except QuestionnaireParameterError as exc:
            return questionnaire_error(str(exc), code=400)

    @app.get("/api/admin/questionnaires/definitions")
    @required
    def questionnaire_admin_definitions():
        try:
            filters = _filters("enabled", "scope_type", "user_type", "occupation_code")
            return questionnaire_response(list_definitions(db.session, filters))
        except QuestionnaireParameterError as exc:
            return questionnaire_error(str(exc), code=400)

    @app.get("/api/admin/questionnaires/definitions/<int:definition_id>")
    @required
    def questionnaire_admin_definition_detail(definition_id: int):
        definition = get_definition(db.session, definition_id)
        if definition is None:
            return questionnaire_error("definition not found", code=404)
        return questionnaire_response(definition)

    @app.get("/api/admin/questionnaires/definitions/<int:definition_id>/versions")
    @required
    def questionnaire_admin_definition_versions(definition_id: int):
        try:
            filters = _filters("status", "current_effective")
        except QuestionnaireParameterError as exc:
            return questionnaire_error(str(exc), code=400)
        if get_definition(db.session, definition_id) is None:
            return questionnaire_error("definition not found", code=404)
        return questionnaire_response(list_versions(db.session, definition_id, filters))

    @app.get("/api/admin/questionnaires/versions/<int:version_id>")
    @required
    def questionnaire_admin_version_detail(version_id: int):
        snapshot = get_version_snapshot(db.session, version_id)
        if snapshot is None:
            return questionnaire_error("version not found", code=404)
        return questionnaire_response(snapshot)

    @app.get("/api/admin/questionnaires/versions/<int:version_id>/preview")
    @required
    def questionnaire_admin_version_preview(version_id: int):
        snapshot = get_version_snapshot(db.session, version_id)
        if snapshot is None:
            return questionnaire_error("version not found", code=404)
        preview = dict(snapshot)
        preview["preview"] = True
        return questionnaire_response(preview)
