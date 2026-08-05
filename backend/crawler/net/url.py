"""Pure, versioned HTTP URL normalization used before every fetch."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit


NORMALIZATION_VERSION = "phase2-v1"
DEFAULT_MAX_URL_LENGTH = 4096
DEFAULT_MAX_HOSTNAME_LENGTH = 253
TRACKING_PARAMETERS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
        "msclkid",
    }
)
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_BAD_PERCENT = re.compile(r"%(?![0-9A-Fa-f]{2})")
_PERCENT_ESCAPE = re.compile(r"%([0-9A-Fa-f]{2})")
_UNRESERVED = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)


class InvalidUrl(ValueError):
    """Raised when a URL cannot cross the crawler network boundary."""


@dataclass(frozen=True, slots=True)
class NormalizedUrl:
    raw_url: str
    url: str
    scheme: str
    hostname: str
    port: int | None
    origin: str
    fingerprint: str
    normalization_version: str = NORMALIZATION_VERSION


def _normalize_percent_escapes(value: str) -> str:
    if _BAD_PERCENT.search(value):
        raise InvalidUrl("URL contains an invalid percent escape")

    def replace(match: re.Match[str]) -> str:
        character = chr(int(match.group(1), 16))
        return character if character in _UNRESERVED else f"%{match.group(1).upper()}"

    return _PERCENT_ESCAPE.sub(replace, value)


def _remove_dot_segments(path: str) -> str:
    trailing_slash = path.endswith(("/.", "/..", "/"))
    segments: list[str] = []
    for segment in path.split("/"):
        if segment in ("", "."):
            continue
        if segment == "..":
            if segments:
                segments.pop()
            continue
        segments.append(segment)
    normalized = "/" + "/".join(segments)
    if trailing_slash and normalized != "/":
        normalized += "/"
    return normalized


def _normalize_hostname(hostname: str, *, max_length: int) -> str:
    if "%" in hostname:
        raise InvalidUrl("IPv6 zone identifiers are not allowed")
    candidate = hostname.rstrip(".").lower()
    if not candidate:
        raise InvalidUrl("URL hostname is required")
    try:
        ascii_hostname = candidate.encode("idna").decode("ascii").lower()
    except UnicodeError as error:
        raise InvalidUrl("URL hostname is not valid IDNA") from error
    if len(ascii_hostname) > max_length:
        raise InvalidUrl("URL hostname is too long")
    if ":" not in ascii_hostname:
        labels = ascii_hostname.split(".")
        if any(not label or len(label) > 63 for label in labels):
            raise InvalidUrl("URL hostname label is invalid")
    return ascii_hostname


def normalize_http_url(
    raw_url: str,
    *,
    max_length: int = DEFAULT_MAX_URL_LENGTH,
    max_hostname_length: int = DEFAULT_MAX_HOSTNAME_LENGTH,
) -> NormalizedUrl:
    """Return a deterministic public-fetch identity without doing DNS I/O."""

    if not isinstance(raw_url, str):
        raise InvalidUrl("URL must be text")
    if max_length < 1 or max_hostname_length < 1:
        raise ValueError("URL limits must be positive")
    if not raw_url.strip():
        raise InvalidUrl("URL must not be empty")
    if len(raw_url) > max_length or _CONTROL.search(raw_url):
        raise InvalidUrl("URL is too long or contains control characters")

    value = raw_url.strip()
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise InvalidUrl("URL contains an invalid port or host") from error
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise InvalidUrl("only HTTP and HTTPS URLs are allowed")
    if parsed.hostname is None:
        raise InvalidUrl("URL hostname is required")
    if parsed.username is not None or parsed.password is not None:
        raise InvalidUrl("URL credentials are not allowed")

    hostname = _normalize_hostname(
        parsed.hostname,
        max_length=max_hostname_length,
    )
    if port == (80 if scheme == "http" else 443):
        port = None
    host_display = f"[{hostname}]" if ":" in hostname else hostname
    netloc = host_display if port is None else f"{host_display}:{port}"

    path = _normalize_percent_escapes(parsed.path or "/")
    path = _remove_dot_segments(path)
    path = quote(path, safe="/%:@!$&'()*+,;=-._~")

    query_items = [
        (key, item_value)
        for key, item_value in parse_qsl(
            parsed.query,
            keep_blank_values=True,
            strict_parsing=False,
        )
        if key.lower() not in TRACKING_PARAMETERS
    ]
    query_items.sort(key=lambda item: (item[0], item[1]))
    query = urlencode(query_items, doseq=True)
    normalized_url = urlunsplit((scheme, netloc, path, query, ""))
    if len(normalized_url) > max_length:
        raise InvalidUrl("normalized URL is too long")
    origin = f"{scheme}://{netloc}"
    return NormalizedUrl(
        raw_url=raw_url,
        url=normalized_url,
        scheme=scheme,
        hostname=hostname,
        port=port,
        origin=origin,
        fingerprint=sha256(normalized_url.encode("utf-8")).hexdigest(),
    )


def same_origin(left: NormalizedUrl, right: NormalizedUrl) -> bool:
    return left.origin == right.origin


def safe_url_for_output(url: str) -> str:
    """Remove query and fragment values from user-visible diagnostics."""

    try:
        normalized = normalize_http_url(url)
    except InvalidUrl:
        return "[invalid-url]"
    parsed = urlsplit(normalized.url)
    suffix = "?[REDACTED]" if parsed.query else ""
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", "")) + suffix
