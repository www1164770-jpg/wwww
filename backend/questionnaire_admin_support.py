"""Response, request parsing, and database-backed access control for new APIs."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException


class QuestionnaireParameterError(ValueError):
    """Raised when a questionnaire read query parameter is invalid."""


def questionnaire_response(
    data: Any = None,
    *,
    message: str = "success",
    code: int = 200,
    legacy_code: int = 0,
    status: int = 200,
):
    """Build the fixed five-key response contract for new questionnaire APIs."""
    return jsonify(
        {
            "code": code,
            "legacy_code": legacy_code,
            "message": message,
            "msg": message,
            "data": {} if data is None else data,
        }
    ), status


def questionnaire_error(
    message: str,
    *,
    code: int,
    data: Any = None,
):
    """Return a new-API error with an explicit matching business code."""
    return questionnaire_response(
        data,
        message=message,
        code=code,
        legacy_code=code,
        status=code,
    )


def optional_boolean(name: str) -> bool | None:
    """Parse one optional true/false query parameter."""
    value = request.args.get(name)
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in ("true", "1"):
        return True
    if normalized in ("false", "0"):
        return False
    raise QuestionnaireParameterError(f"{name} must be true or false")


def optional_text(name: str) -> str | None:
    """Return a supplied non-empty filter value, or no filter."""
    value = request.args.get(name)
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise QuestionnaireParameterError(f"{name} must not be empty")
    return value


def pagination_filters() -> dict[str, int]:
    """Return validated, service-compatible paging values."""
    values: dict[str, int] = {}
    for name, default in (("page", 1), ("page_size", 20)):
        raw_value = request.args.get(name)
        if raw_value is None:
            values[name] = default
            continue
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise QuestionnaireParameterError(f"{name} must be a positive integer") from exc
        if value < 1:
            raise QuestionnaireParameterError(f"{name} must be a positive integer")
        values[name] = value
    return values


def questionnaire_admin_required(get_db_connection: Callable[[], Any]):
    """Require a valid JWT plus a fresh administrator role query."""

    def decorator(fn):
        @wraps(fn)
        def wrapped(*args: Any, **kwargs: Any):
            try:
                verify_jwt_in_request()
            except JWTExtendedException:
                return questionnaire_error("unauthorized", code=401)

            identity = get_jwt_identity()
            with get_db_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT * FROM users WHERE username=%s OR email=%s",
                        (identity, identity),
                    )
                    user = cursor.fetchone()
            if not user or user.get("role") not in ("admin", "super_admin"):
                return questionnaire_error("forbidden", code=403)
            return fn(*args, **kwargs)

        return wrapped

    return decorator
