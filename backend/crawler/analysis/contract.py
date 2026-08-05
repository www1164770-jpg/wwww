"""Bounded, deterministic Phase 3 traceability contracts.

The objects in this module are deliberately independent of a provider or a
database connection so their safety properties can be tested offline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any

from backend.crawler.observability.json_logging import redact_sensitive


_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MAX_DEPTH = 5
_MAX_ITEMS = 24
_MAX_TEXT = 2048
_SENSITIVE_QUERY = {"token", "access_token", "api_key", "key", "password", "secret", "signature"}


def bounded_text(value: object | None, limit: int) -> str | None:
    if value is None:
        return None
    return _CONTROL.sub("", str(value)).strip()[:limit] or None


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _safe_url(value: str | None) -> str | None:
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
    text = bounded_text(value, 4096)
    if not text:
        return None
    parts = urlsplit(text)
    query = urlencode([(key, "[REDACTED]" if key.lower() in _SENSITIVE_QUERY else val)
                       for key, val in parse_qsl(parts.query, keep_blank_values=True)])
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def sanitize_provider_response(value: Any, *, max_depth: int = _MAX_DEPTH, max_items: int = _MAX_ITEMS, max_text: int = _MAX_TEXT) -> Any:
    """Redact and bound arbitrary provider output before it can be persisted."""
    if max_depth < 1 or max_items < 1 or max_text < 1:
        raise ValueError("provider response bounds must be positive")

    def visit(item: Any, depth: int, key: str | None = None) -> Any:
        if depth >= max_depth:
            return "[TRUNCATED_DEPTH]"
        if isinstance(item, dict):
            return {bounded_text(k, 128) or "": visit(v, depth + 1, str(k))
                    for k, v in list(item.items())[:max_items]}
        if isinstance(item, (list, tuple)):
            return [visit(v, depth + 1, key) for v in item[:max_items]]
        if isinstance(item, str):
            safe = redact_sensitive(_safe_url(item) if item.startswith(("http://", "https://")) else item, key=key)
            return bounded_text(safe, max_text) or ""
        if item is None or isinstance(item, (bool, int, float)):
            return item
        return bounded_text(redact_sensitive(str(item), key=key), max_text) or ""

    return visit(value, 0)


@dataclass(frozen=True, slots=True)
class AnalysisSpec:
    analyzer_type: str = "rules"
    provider_name: str = ""
    model_version: str = ""
    prompt_version: str = "v1"
    taxonomy_version: str = "v1"
    scoring_version: str = "v1"
    schema_version: str = "v1"

    def payload(self) -> dict[str, str]:
        return {key: bounded_text(value, 128) or "" for key, value in asdict(self).items()}


def analysis_key(*, fetch_result_uid: str, content_hash: str, spec: AnalysisSpec) -> str:
    return digest({"fetch_result_uid": fetch_result_uid, "content_hash": content_hash, **spec.payload()})


def input_snapshot(*, title: str | None, meta_description: str | None, heading: str | None, text_excerpt: str | None, normalized_url: str | None, language: str | None, content_type: str | None, content_hash: str) -> dict[str, str | None]:
    return {
        "title": bounded_text(title, 500), "meta_description": bounded_text(meta_description, 2000),
        "heading": bounded_text(heading, 1000), "text_excerpt": bounded_text(text_excerpt, 4000),
        "normalized_url": _safe_url(normalized_url), "language": bounded_text(language, 16),
        "content_type": bounded_text(content_type, 128), "content_hash": bounded_text(content_hash, 64),
    }

