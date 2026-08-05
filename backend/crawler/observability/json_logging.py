"""Single-line JSON crawler logging with mandatory sensitive-data redaction."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
import logging
from logging.handlers import TimedRotatingFileHandler
import re
import sys
from typing import Any, TextIO
from uuid import uuid4

from backend.crawler.config import CrawlerSettings


REQUIRED_CONTEXT_FIELDS = (
    "worker_id",
    "run_uid",
    "task_uid",
    "duration_ms",
    "error_code",
)
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "apikey",
    "database_url",
)
_SENSITIVE_EXACT_KEYS = frozenset(
    {
        "body",
        "content",
        "html",
        "page_text",
        "raw_text",
        "response_body",
        "payload",
        "email",
        "phone",
        "phone_number",
        "id_card",
        "personal_data",
    }
)
_URL_PASSWORD = re.compile(
    r"(?i)([a-z][a-z0-9+.-]*://[^:/@\s]+:)[^@/\s]+@"
)
_HEADER_SECRET = re.compile(
    r"(?i)\b(authorization|cookie)\s*[:=]\s*[^;,\r\n]+"
)
_VALUE_SECRET = re.compile(
    r"(?i)\b(password|passwd|token|secret|api[_-]?key)\s*[:=]\s*[^;,\s]+"
)
_VALID_ERROR_CODE = re.compile(r"[A-Za-z0-9_.-]+")


def _normalized_key(key: str | None) -> str:
    return (key or "").strip().lower().replace("-", "_")


def redact_sensitive(value: Any, *, key: str | None = None) -> Any:
    """Return a copy safe for logs or worker diagnostic metadata."""

    normalized_key = _normalized_key(key)
    if normalized_key in _SENSITIVE_EXACT_KEYS or any(
        part in normalized_key for part in _SENSITIVE_KEY_PARTS
    ):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {
            str(item_key): redact_sensitive(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, str):
        return _URL_PASSWORD.sub(r"\1[REDACTED]@", value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return deepcopy(str(value))


def sanitize_error_message(message: str, *, max_length: int = 1000) -> str:
    if max_length < 1:
        raise ValueError("crawler error message limit must be positive")
    lines = str(message).splitlines()
    first_line = lines[0] if lines else ""
    if "<html" in first_line.lower() or "<!doctype" in first_line.lower():
        return "[response body omitted]"[:max_length]
    sanitized = redact_sensitive(first_line)
    sanitized = _HEADER_SECRET.sub(r"\1=[REDACTED]", sanitized)
    sanitized = _VALUE_SECRET.sub(r"\1=[REDACTED]", sanitized)
    return sanitized[:max_length]


def sanitize_error_code(code: str | None, *, max_length: int = 64) -> str | None:
    if code is None:
        return None
    if max_length < 1:
        raise ValueError("crawler error code limit must be positive")
    normalized = str(code).strip()
    if not normalized:
        return "unknown_error"
    if _VALID_ERROR_CODE.fullmatch(normalized) is None:
        return "invalid_error_code"
    return normalized[:max_length]


class CrawlerJsonFormatter(logging.Formatter):
    """Format crawler events as stable, single-line JSON."""

    def __init__(self, *, component: str) -> None:
        super().__init__()
        self.component = component

    def format(self, record: logging.LogRecord) -> str:
        context = getattr(record, "crawler_context", {})
        payload: dict[str, Any] = {
            "timestamp": (
                datetime.fromtimestamp(record.created, UTC)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z")
            ),
            "level": record.levelname,
            "component": self.component,
            "event": getattr(record, "crawler_event", "log_message"),
        }
        for field in REQUIRED_CONTEXT_FIELDS:
            value = context.get(field)
            payload[field] = (
                sanitize_error_code(value)
                if field == "error_code"
                else redact_sensitive(value, key=field)
            )
        details = redact_sensitive(context.get("details", {}))
        if details:
            payload["details"] = details
        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )


def _stream_handler(
    stream: TextIO,
    *,
    component: str,
) -> logging.Handler:
    handler = logging.StreamHandler(stream)
    handler.setFormatter(CrawlerJsonFormatter(component=component))
    return handler


def configure_crawler_logging(
    settings: CrawlerSettings,
    *,
    component: str,
    stream: TextIO | None = None,
    force_file_attempt: bool = False,
) -> logging.Logger:
    """Create an isolated crawler logger without changing application logging."""

    normalized_component = component.strip()
    if not normalized_component:
        raise ValueError("crawler log component must not be blank")
    logger = logging.getLogger(
        f"zhihui.crawler.{normalized_component}.{uuid4().hex}"
    )
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if stream is not None and not force_file_attempt:
        logger.addHandler(
            _stream_handler(stream, component=normalized_component)
        )
        return logger

    try:
        settings.log_root.mkdir(parents=True, exist_ok=True)
        handler = TimedRotatingFileHandler(
            settings.log_root / "crawler.jsonl",
            when="midnight",
            backupCount=30,
            encoding="utf-8",
            utc=True,
        )
        handler.setFormatter(
            CrawlerJsonFormatter(component=normalized_component)
        )
        logger.addHandler(handler)
    except (OSError, RuntimeError) as error:
        logger.addHandler(
            _stream_handler(
                stream or sys.stderr,
                component=normalized_component,
            )
        )
        log_event(
            logger,
            "logging_fallback",
            error_code=type(error).__name__,
        )
    return logger


def log_event(
    logger: logging.Logger,
    event: str,
    **fields: Any,
) -> None:
    normalized_event = event.strip()
    if not normalized_event:
        raise ValueError("crawler log event must not be blank")
    context = {
        field: fields.pop(field, None) for field in REQUIRED_CONTEXT_FIELDS
    }
    context["details"] = fields
    logger.info(
        "",
        extra={
            "crawler_event": normalized_event,
            "crawler_context": context,
        },
    )
