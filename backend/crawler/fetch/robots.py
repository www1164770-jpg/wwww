"""Conservative robots.txt evaluation and per-origin caching."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
import threading
from collections.abc import Callable
from urllib.parse import urlsplit

from backend.crawler.net.url import normalize_http_url
from backend.crawler.errors import Cancelled


@dataclass(frozen=True, slots=True)
class RobotsResponse:
    status_code: int
    body: bytes


@dataclass(frozen=True, slots=True)
class RobotsDecision:
    allowed: bool
    status_code: int | None
    crawl_delay: float | None
    sitemaps: tuple[str, ...]
    checked_at: datetime
    expires_at: datetime
    matched_rule: str | None = None
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class _Rule:
    allow: bool
    pattern: str

    def matches(self, path: str) -> bool:
        escaped = re.escape(self.pattern).replace(r"\*", ".*")
        if escaped.endswith(r"\$"):
            escaped = escaped[:-2] + "$"
        return re.match("^" + escaped, path) is not None


@dataclass(frozen=True, slots=True)
class _ParsedRobots:
    rules: tuple[_Rule, ...]
    crawl_delay: float | None
    sitemaps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    status_code: int | None
    parsed: _ParsedRobots
    checked_at: datetime
    expires_at: datetime
    forced_error: str | None
    forced_allowed: bool | None


def _decode(body: bytes) -> str:
    return body[:512_000].decode("utf-8-sig", errors="replace")


def _parse(body: bytes, user_agent: str) -> _ParsedRobots:
    groups: list[tuple[list[str], list[_Rule], float | None]] = []
    agents: list[str] = []
    rules: list[_Rule] = []
    delay: float | None = None
    sitemaps: list[str] = []
    seen_directive = False

    def finish_group() -> None:
        nonlocal agents, rules, delay, seen_directive
        if agents:
            groups.append((agents, rules, delay))
        agents, rules, delay, seen_directive = [], [], None, False

    for raw_line in _decode(body).splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, value = (part.strip() for part in line.split(":", 1))
        field = field.lower()
        if field == "user-agent":
            if seen_directive:
                finish_group()
            agents.append(value.lower())
            continue
        if field == "sitemap":
            if value:
                sitemaps.append(value)
            continue
        if not agents:
            continue
        if field in {"allow", "disallow"}:
            seen_directive = True
            if value:
                rules.append(_Rule(field == "allow", value))
        elif field == "crawl-delay":
            seen_directive = True
            try:
                parsed_delay = float(value)
            except ValueError:
                continue
            if 0 <= parsed_delay <= 86400:
                delay = parsed_delay
    finish_group()

    product = user_agent.split("/", 1)[0].lower()
    scores = [
        max(
            (len(agent) if agent != "*" and agent in product else 0)
            for agent in group_agents
        )
        for group_agents, _rules, _delay in groups
    ]
    best = max(scores, default=0)
    selected = [
        group
        for group, score in zip(groups, scores)
        if score == best and score > 0
    ]
    if not selected:
        selected = [group for group in groups if "*" in group[0]]
    selected_rules = tuple(rule for _a, items, _d in selected for rule in items)
    selected_delays = [value for _a, _r, value in selected if value is not None]
    return _ParsedRobots(
        rules=selected_rules,
        crawl_delay=max(selected_delays, default=None),
        sitemaps=tuple(dict.fromkeys(sitemaps)),
    )


class RobotsCache:
    def __init__(
        self,
        *,
        loader: Callable[[str, threading.Event], RobotsResponse],
        user_agent: str,
        ttl_seconds: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not user_agent.strip():
            raise ValueError("robots user agent must not be blank")
        if ttl_seconds < 1:
            raise ValueError("robots cache lifetime must be positive")
        self._loader = loader
        self._user_agent = user_agent
        self._ttl = timedelta(seconds=ttl_seconds)
        self._clock = clock or (lambda: datetime.now(timezone.utc).replace(tzinfo=None))
        self._entries: dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()

    def _load(self, origin: str, cancel_event: threading.Event) -> _CacheEntry:
        now = self._clock()
        status: int | None = None
        parsed = _ParsedRobots((), None, ())
        forced_error: str | None = None
        forced_allowed: bool | None = None
        try:
            response = self._loader(f"{origin}/robots.txt", cancel_event)
            status = response.status_code
            if 200 <= status < 300:
                parsed = _parse(response.body, self._user_agent)
            elif status == 404:
                forced_allowed = True
            elif status in {401, 403, 429}:
                forced_allowed = False
                forced_error = f"robots_http_{status}"
            elif status >= 500:
                forced_allowed = False
                forced_error = "robots_http_5xx"
            else:
                forced_allowed = False
                forced_error = "robots_http_4xx"
        except Cancelled:
            raise
        except Exception:
            forced_allowed = False
            forced_error = "robots_network_failure"
        return _CacheEntry(
            status,
            parsed,
            now,
            now + self._ttl,
            forced_error,
            forced_allowed,
        )

    def check(
        self,
        url: str,
        *,
        cancel_event: threading.Event | None = None,
    ) -> RobotsDecision:
        normalized = normalize_http_url(url)
        origin = normalized.origin
        event = cancel_event or threading.Event()
        now = self._clock()
        with self._lock:
            entry = self._entries.get(origin)
        if entry is None or entry.expires_at <= now:
            entry = self._load(origin, event)
            with self._lock:
                self._entries[origin] = entry

        path = urlsplit(normalized.url).path or "/"
        query = urlsplit(normalized.url).query
        target = path + (f"?{query}" if query else "")
        matched: _Rule | None = None
        if entry.forced_allowed is None:
            candidates = [rule for rule in entry.parsed.rules if rule.matches(target)]
            if candidates:
                matched = max(candidates, key=lambda item: (len(item.pattern), item.allow))
            allowed = matched.allow if matched is not None else True
        else:
            allowed = entry.forced_allowed
        return RobotsDecision(
            allowed=allowed,
            status_code=entry.status_code,
            crawl_delay=entry.parsed.crawl_delay,
            sitemaps=entry.parsed.sitemaps,
            checked_at=entry.checked_at,
            expires_at=entry.expires_at,
            matched_rule=matched.pattern if matched is not None else None,
            error_code=entry.forced_error,
        )

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
