"""Parse crawler-only runtime configuration without application side effects."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import time
import os
from pathlib import Path
import socket


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class CrawlerConfigError(ValueError):
    """Raised when crawler-specific configuration is missing or invalid."""


def _positive_integer(
    environ: Mapping[str, str],
    key: str,
    default: int,
) -> int:
    raw_value = environ.get(key, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as error:
        raise CrawlerConfigError(f"{key} must be a positive integer") from error
    if value <= 0:
        raise CrawlerConfigError(f"{key} must be a positive integer")
    return value


def _bounded_integer(
    environ: Mapping[str, str],
    key: str,
    default: int,
    *,
    minimum: int,
    maximum: int,
) -> int:
    raw_value = environ.get(key, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as error:
        raise CrawlerConfigError(f"{key} must be an integer") from error
    if not minimum <= value <= maximum:
        raise CrawlerConfigError(
            f"{key} must be between {minimum} and {maximum}"
        )
    return value


def _bounded_float(
    environ: Mapping[str, str],
    key: str,
    default: float,
    *,
    minimum: float,
    maximum: float,
) -> float:
    raw_value = environ.get(key, str(default)).strip()
    try:
        value = float(raw_value)
    except ValueError as error:
        raise CrawlerConfigError(f"{key} must be numeric") from error
    if not minimum <= value <= maximum:
        raise CrawlerConfigError(
            f"{key} must be between {minimum} and {maximum}"
        )
    return value


def _clock_time(environ: Mapping[str, str], key: str, default: str) -> time:
    raw_value = environ.get(key, default).strip()
    try:
        hour_text, minute_text = raw_value.split(":")
        if len(hour_text) != 2 or len(minute_text) != 2:
            raise ValueError
        hour = int(hour_text)
        minute = int(minute_text)
        value = time(hour, minute)
    except (TypeError, ValueError) as error:
        raise CrawlerConfigError(f"{key} must use 24-hour HH:MM format") from error
    return value


def _boolean(environ: Mapping[str, str], key: str, default: bool) -> bool:
    raw_value = environ.get(key, "true" if default else "false").strip().lower()
    if raw_value in {"1", "true", "yes", "on"}:
        return True
    if raw_value in {"0", "false", "no", "off"}:
        return False
    raise CrawlerConfigError(f"{key} must be a boolean")


def _runtime_path(
    environ: Mapping[str, str],
    key: str,
    default: str,
) -> Path:
    raw_value = environ.get(key, "").strip() or default
    path = Path(raw_value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


@dataclass(frozen=True, slots=True)
class CrawlerSettings:
    """Validated settings for crawler commands and workers."""

    database_url: str | None
    icon_root: Path
    log_root: Path
    worker_id: str
    lease_seconds: int
    max_attempts: int
    nightly_target: int
    start_time: time
    stop_time: time
    user_agent: str = "ZhiHuiNavigationBot/1.0"
    global_concurrency: int = 5
    domain_delay_seconds: float = 1.0
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 10.0
    max_response_bytes: int = 2_097_152
    max_redirects: int = 5
    max_depth: int = 2
    max_pages_per_origin: int = 20
    max_links_per_page: int = 200
    max_urls_per_run: int = 100
    robots_cache_seconds: int = 86_400
    dns_cache_seconds: int = 60
    max_sitemap_bytes: int = 5_242_880
    max_sitemap_urls: int = 1000
    max_sitemap_files: int = 20
    max_sitemap_depth: int = 3
    max_feed_entries: int = 100
    max_retries: int = 3
    analysis_enabled: bool = False
    icon_fetch_enabled: bool = False
    analysis_confidence_threshold: float = 0.85
    analysis_rule_version: str = "analysis-rules-v1"
    risk_rule_version: str = "risk-rules-v1"
    ollama_endpoint: str = "http://127.0.0.1:11434/api/generate"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: float = 20.0
    icon_max_bytes: int = 1_048_576
    icon_max_pixels: int = 16_777_216
    icon_max_redirects: int = 3
    analyzer_type: str = "rules"
    analysis_provider: str = ""
    analysis_model_version: str = ""
    analysis_max_input_chars: int = 20_000
    analysis_max_output_chars: int = 10_000
    analysis_max_retries: int = 3
    analysis_taxonomy_version: str = "v1"
    analysis_scoring_version: str = "v1"
    analysis_prompt_version: str = "v1"
    analysis_schema_version: str = "v1"
    nav_site_sync_enabled: bool = False
    nav_site_database_url: str | None = None
    nav_site_allowed_database: str | None = None
    publish_max_retries: int = 3
    publish_retry_base_seconds: int = 5
    publish_preview_ttl_seconds: int = 3600

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        require_database: bool = False,
    ) -> "CrawlerSettings":
        values = os.environ if environ is None else environ
        database_url = values.get("CRAWLER_DATABASE_URL", "").strip() or None
        if require_database and database_url is None:
            raise CrawlerConfigError(
                "CRAWLER_DATABASE_URL is required for crawler commands"
            )

        worker_id = values.get("CRAWLER_WORKER_ID", "").strip()
        if "CRAWLER_WORKER_ID" in values and not worker_id:
            raise CrawlerConfigError("CRAWLER_WORKER_ID must not be blank")
        if not worker_id:
            worker_id = f"{socket.gethostname()}-{os.getpid()}"

        user_agent = values.get(
            "CRAWLER_USER_AGENT",
            "ZhiHuiNavigationBot/1.0",
        ).strip()
        if (
            not user_agent
            or len(user_agent) > 255
            or any(ord(character) < 32 or ord(character) == 127 for character in user_agent)
        ):
            raise CrawlerConfigError("CRAWLER_USER_AGENT must be a safe non-blank value")

        start_time = _clock_time(values, "CRAWLER_START_TIME", "01:00")
        stop_time = _clock_time(values, "CRAWLER_STOP_TIME", "05:00")
        if start_time >= stop_time:
            raise CrawlerConfigError(
                "CRAWLER_STOP_TIME must be later than CRAWLER_START_TIME"
            )

        return cls(
            database_url=database_url,
            icon_root=_runtime_path(
                values,
                "CRAWLER_ICON_ROOT",
                "backend/data/crawler/icons",
            ),
            log_root=_runtime_path(
                values,
                "CRAWLER_LOG_ROOT",
                "backend/data/crawler/logs",
            ),
            worker_id=worker_id,
            lease_seconds=_positive_integer(
                values,
                "CRAWLER_LEASE_SECONDS",
                300,
            ),
            max_attempts=_positive_integer(
                values,
                "CRAWLER_MAX_ATTEMPTS",
                3,
            ),
            nightly_target=_positive_integer(
                values,
                "CRAWLER_NIGHTLY_TARGET",
                3000,
            ),
            start_time=start_time,
            stop_time=stop_time,
            user_agent=user_agent,
            global_concurrency=_bounded_integer(
                values, "CRAWLER_GLOBAL_CONCURRENCY", 5, minimum=1, maximum=100
            ),
            domain_delay_seconds=_bounded_float(
                values, "CRAWLER_DOMAIN_DELAY_SECONDS", 1, minimum=0.001, maximum=3600
            ),
            connect_timeout_seconds=_bounded_float(
                values, "CRAWLER_CONNECT_TIMEOUT_SECONDS", 5, minimum=0.1, maximum=300
            ),
            read_timeout_seconds=_bounded_float(
                values, "CRAWLER_READ_TIMEOUT_SECONDS", 10, minimum=0.1, maximum=600
            ),
            max_response_bytes=_bounded_integer(
                values, "CRAWLER_MAX_RESPONSE_BYTES", 2_097_152, minimum=1024, maximum=104_857_600
            ),
            max_redirects=_bounded_integer(
                values, "CRAWLER_MAX_REDIRECTS", 5, minimum=1, maximum=20
            ),
            max_depth=_bounded_integer(
                values, "CRAWLER_MAX_DEPTH", 2, minimum=1, maximum=10
            ),
            max_pages_per_origin=_bounded_integer(
                values, "CRAWLER_MAX_PAGES_PER_ORIGIN", 20, minimum=1, maximum=10_000
            ),
            max_links_per_page=_bounded_integer(
                values, "CRAWLER_MAX_LINKS_PER_PAGE", 200, minimum=1, maximum=10_000
            ),
            max_urls_per_run=_bounded_integer(
                values, "CRAWLER_MAX_URLS_PER_RUN", 100, minimum=1, maximum=100_000
            ),
            robots_cache_seconds=_bounded_integer(
                values, "CRAWLER_ROBOTS_CACHE_SECONDS", 86_400, minimum=1, maximum=604_800
            ),
            dns_cache_seconds=_bounded_integer(
                values, "CRAWLER_DNS_CACHE_SECONDS", 60, minimum=1, maximum=300
            ),
            max_sitemap_bytes=_bounded_integer(
                values, "CRAWLER_MAX_SITEMAP_BYTES", 5_242_880, minimum=1024, maximum=104_857_600
            ),
            max_sitemap_urls=_bounded_integer(
                values, "CRAWLER_MAX_SITEMAP_URLS", 1000, minimum=1, maximum=1_000_000
            ),
            max_sitemap_files=_bounded_integer(
                values, "CRAWLER_MAX_SITEMAP_FILES", 20, minimum=1, maximum=1000
            ),
            max_sitemap_depth=_bounded_integer(
                values, "CRAWLER_MAX_SITEMAP_DEPTH", 3, minimum=1, maximum=20
            ),
            max_feed_entries=_bounded_integer(
                values, "CRAWLER_MAX_FEED_ENTRIES", 100, minimum=1, maximum=10_000
            ),
            max_retries=_bounded_integer(
                values, "CRAWLER_MAX_RETRIES", 3, minimum=1, maximum=10
            ),
            analysis_enabled=_boolean(values, "CRAWLER_ANALYSIS_ENABLED", False),
            icon_fetch_enabled=_boolean(values, "CRAWLER_ICON_FETCH_ENABLED", False),
            analysis_confidence_threshold=_bounded_float(
                values,
                "CRAWLER_ANALYSIS_CONFIDENCE_THRESHOLD",
                0.85,
                minimum=0.5,
                maximum=1.0,
            ),
            analysis_rule_version=(
                values.get("CRAWLER_ANALYSIS_RULE_VERSION", "analysis-rules-v1").strip()
                or "analysis-rules-v1"
            )[:128],
            risk_rule_version=(
                values.get("CRAWLER_RISK_RULE_VERSION", "risk-rules-v1").strip()
                or "risk-rules-v1"
            )[:128],
            ollama_endpoint=(
                values.get(
                    "CRAWLER_OLLAMA_ENDPOINT",
                    "http://127.0.0.1:11434/api/generate",
                ).strip()
                or "http://127.0.0.1:11434/api/generate"
            ),
            ollama_model=(
                values.get("CRAWLER_OLLAMA_MODEL", "qwen2.5:3b").strip()
                or "qwen2.5:3b"
            )[:255],
            ollama_timeout_seconds=_bounded_float(
                values,
                "CRAWLER_OLLAMA_TIMEOUT_SECONDS",
                20,
                minimum=0.1,
                maximum=120,
            ),
            icon_max_bytes=_bounded_integer(
                values,
                "CRAWLER_ICON_MAX_BYTES",
                1_048_576,
                minimum=1024,
                maximum=10_485_760,
            ),
            icon_max_pixels=_bounded_integer(
                values,
                "CRAWLER_ICON_MAX_PIXELS",
                16_777_216,
                minimum=256,
                maximum=67_108_864,
            ),
            icon_max_redirects=_bounded_integer(
                values,
                "CRAWLER_ICON_MAX_REDIRECTS",
                3,
                minimum=1,
                maximum=10,
            ),
            analyzer_type=(values.get("CRAWLER_ANALYZER_TYPE", "rules").strip() or "rules")[:32],
            analysis_provider=(values.get("CRAWLER_ANALYSIS_PROVIDER", "").strip())[:128],
            analysis_model_version=(values.get("CRAWLER_ANALYSIS_MODEL_VERSION", "").strip())[:128],
            analysis_max_input_chars=_bounded_integer(values, "CRAWLER_ANALYSIS_MAX_INPUT_CHARS", 20_000, minimum=100, maximum=100_000),
            analysis_max_output_chars=_bounded_integer(values, "CRAWLER_ANALYSIS_MAX_OUTPUT_CHARS", 10_000, minimum=100, maximum=100_000),
            analysis_max_retries=_bounded_integer(values, "CRAWLER_ANALYSIS_MAX_RETRIES", 3, minimum=1, maximum=10),
            analysis_taxonomy_version=(values.get("CRAWLER_ANALYSIS_TAXONOMY_VERSION", "v1").strip() or "v1")[:128],
            analysis_scoring_version=(values.get("CRAWLER_ANALYSIS_SCORING_VERSION", "v1").strip() or "v1")[:128],
            analysis_prompt_version=(values.get("CRAWLER_ANALYSIS_PROMPT_VERSION", "v1").strip() or "v1")[:128],
            analysis_schema_version=(values.get("CRAWLER_ANALYSIS_SCHEMA_VERSION", "v1").strip() or "v1")[:128],
            nav_site_sync_enabled=_boolean(values, "CRAWLER_NAV_SITE_SYNC_ENABLED", False),
            nav_site_database_url=values.get("CRAWLER_NAV_SITE_DATABASE_URL", "").strip() or None,
            nav_site_allowed_database=values.get("CRAWLER_NAV_SITE_ALLOWED_DATABASE", "").strip() or None,
            publish_max_retries=_bounded_integer(values, "CRAWLER_PUBLISH_MAX_RETRIES", 3, minimum=1, maximum=20),
            publish_retry_base_seconds=_bounded_integer(values, "CRAWLER_PUBLISH_RETRY_BASE_SECONDS", 5, minimum=1, maximum=86_400),
            publish_preview_ttl_seconds=_bounded_integer(values, "CRAWLER_PUBLISH_PREVIEW_TTL_SECONDS", 3600, minimum=60, maximum=604_800),
        )
