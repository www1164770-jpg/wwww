"""Public candidate retrieval shared by ordinary search and AI intent ranking.

No user/favorite data enters this service or its index. SQL is the authority for
visibility. Only transport/service outages cause database fault fallback.
"""
import hashlib
import json
import logging
import os
import time
from urllib.parse import urlsplit

import requests

log = logging.getLogger(__name__)
VERSION = "search-v2"
SETTINGS = {
    "searchableAttributes": ["name", "aliases", "tags", "summary", "description", "use_cases", "occupations", "category_name", "url"],
    "filterableAttributes": ["category_id", "tags", "occupations", "status", "enabled"],
    "sortableAttributes": ["click_count", "recommend_level", "quality_score", "updated_at", "id"],
    "rankingRules": ["words", "typo", "proximity", "attribute", "exactness", "sort"],
    "pagination": {"maxTotalHits": 100000},
}


class SearchUnavailable(RuntimeError):
    pass


class SearchConfigurationError(RuntimeError):
    pass


class Meili:
    def __init__(self, host, key=None, index="websites", timeout=3):
        parsed = urlsplit(host)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise SearchConfigurationError("Invalid MEILI_HOST")
        if not index.replace("_", "").replace("-", "").isalnum():
            raise SearchConfigurationError("Invalid MEILI_INDEX")
        self.host, self.index, self.timeout = host.rstrip("/"), index, timeout
        self.session = requests.Session()
        if key:
            self.session.headers["Authorization"] = "Bearer " + key

    def request(self, method, path, body=None):
        try:
            response = self.session.request(method, self.host + path, json=body, timeout=self.timeout)
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise SearchUnavailable(type(exc).__name__) from None
        if response.status_code >= 500 or response.status_code == 429:
            raise SearchUnavailable("meili_http_" + str(response.status_code))
        if not response.ok:
            # Never expose request bodies, credentials or upstream exception text.
            raise SearchConfigurationError("meili_http_" + str(response.status_code))
        return response.json() if response.content else {}

    def wait(self, uid, seconds=30):
        deadline = time.monotonic() + seconds
        while True:
            result = self.request("GET", f"/tasks/{uid}")
            if result["status"] == "succeeded":
                return result
            if result["status"] in ("failed", "canceled"):
                raise SearchConfigurationError("meili_task_" + result["status"])
            if time.monotonic() >= deadline:
                raise SearchUnavailable("meili_task_timeout")
            time.sleep(.05)

    def candidates(self, queries, category=None, max_candidates=None):
        ids = []
        for query in dict.fromkeys(queries):
            page = 1
            while True:
                body = {"q": query, "page": page, "hitsPerPage": 500,
                        "attributesToRetrieve": ["id"], "matchingStrategy": "all"}
                if category is not None:
                    body["filter"] = f"category_id = {int(category)}"
                result = self.request("POST", f"/indexes/{self.index}/search", body)
                ids.extend(int(row["id"]) for row in result["hits"])
                if max_candidates is not None and len(set(ids)) > max_candidates:
                    return set(list(dict.fromkeys(ids))[:max_candidates+1])
                if page >= result["totalPages"]:
                    break
                page += 1
        return set(ids)

    def documents(self, index=None):
        index = index or self.index
        documents, offset = [], 0
        while True:
            page = self.request("GET", f"/indexes/{index}/documents?offset={offset}&limit=500")
            documents.extend(page["results"])
            offset += len(page["results"])
            if offset >= page["total"] or not page["results"]:
                return documents


def public(row):
    return row.get("status") in ("approved", "active") and row.get("enabled", 1) in (1, True)


def document(row):
    fields = ("id", "name", "url", "aliases", "summary", "description", "tags", "occupations", "use_cases", "category_id", "category_name", "status", "enabled", "click_count", "recommend_level", "quality_score", "updated_at")
    result = {key: row.get(key) for key in fields}
    result["enabled"] = row.get("enabled", 1)
    result["updated_at"] = str(row.get("updated_at") or "")
    result["fingerprint"] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
    return result


def matches(row, groups, match_all=True):
    values = " ".join(str(row.get(key) or "") for key in SETTINGS["searchableAttributes"]).casefold()
    hits = [any(str(term).casefold() in values for term in group) for group in groups]
    return (all(hits) if match_all else any(hits)) if hits else True


class SearchService:
    def __init__(self, catalog, meili=None, redis=None):
        self.catalog, self.meili, self.redis = catalog, meili, redis

    def retrieve(self, query, groups, *, category=None, sort="relevance", page=1, page_size=20, ai=False, candidate_limit=None):
        started = time.perf_counter()
        # Always obtain current rows, even on cache hits. This closes visibility,
        # changed-category and missing-page gaps during asynchronous indexing.
        revision, indexed, rows = self.catalog.snapshot()
        rows = [r for r in rows if public(r) and (category is None or r.get("category_id") == category)]
        synchronized = revision == indexed and revision is not None
        if candidate_limit is not None and not 1 <= candidate_limit <= 10000:
            raise ValueError("candidate limit outside supported range")
        namespace = [self.catalog.engine.url.host, self.catalog.engine.url.port, str(self.catalog.engine.url.database), self.meili.host if self.meili else "database", self.meili.index if self.meili else None, candidate_limit]
        key = VERSION + ":" + hashlib.sha256(json.dumps([namespace, query, groups, category, sort, page, page_size, ai, revision, indexed], ensure_ascii=False).encode()).hexdigest()
        cached, ids, source, reason, relaxed = False, None, "database", None, False
        if self.meili and synchronized and self.redis:
            try:
                value = self.redis.get(key)
                if value is not None:
                    payload = json.loads(value)
                    ids, cached, relaxed = set(payload["ids"]), True, payload["relaxed"]
                    source = "meilisearch"
            except Exception:
                log.warning("search_cache_unavailable")
        if ids is None and self.meili:
            try:
                # Union controlled aliases/AI terms; existing ranking remains authoritative.
                if ai:
                    ids = self.meili.candidates([query] + [str(t) for group in groups for t in group], category, max_candidates=candidate_limit)
                else:
                    sets = [self.meili.candidates(list(group), category) for group in groups]
                    ids = set.intersection(*sets) if sets else self.meili.candidates([query], category)
                    if not ids and len(sets) > 1:
                        ids, relaxed = set.union(*sets), True
                source = "meilisearch"
                if synchronized and self.redis:
                    try:
                        self.redis.setex(key, 300, json.dumps({"ids": sorted(ids), "relaxed": relaxed}))
                    except Exception:
                        log.warning("search_cache_unavailable")
            except SearchUnavailable as exc:
                reason = str(exc)
                log.warning("search_database_fallback reason=%s", reason)
        if not self.meili:
            reason = "explicit_database_mode"
        if ids is not None:
            selected = [row for row in rows if row["id"] in ids]
            if not synchronized:
                # A declared consistency overlay, not a zero-result fault fallback.
                # Re-evaluate the current catalog while committed events are pending.
                selected = [row for row in rows if matches(row, groups, not ai)]
                source = "meilisearch+pending_database"
                cached = False
        else:
            selected = [row for row in rows if matches(row, groups, not ai)]
        if not selected and len(groups) > 1 and (ids is None or not synchronized):
            selected = [row for row in rows if matches(row, groups, False)]
            relaxed = bool(selected)
        # Preserve existing full-URL de-duplication, never lower path/query.
        unique, seen = [], set()
        for row in selected:
            parsed = urlsplit(str(row.get("url") or ""))
            identity = parsed._replace(scheme=parsed.scheme.lower(), netloc=parsed.netloc.lower()).geturl()
            if identity and identity not in seen:
                seen.add(identity)
                unique.append(row)
        meta = {"source": source, "fallbackReason": reason, "cached": cached,
                "dataVersion": f"{VERSION}:{revision}:{indexed}", "relaxed": relaxed,
                "durationMs": round((time.perf_counter() - started) * 1000, 3)}
        meta["truncated"] = candidate_limit is not None and (len(unique)>candidate_limit or ids is not None and len(ids)>candidate_limit)
        if candidate_limit is not None:
            unique=unique[:candidate_limit]
        log.info("search_retrieval source=%s duration_ms=%s fallback=%s", source, meta["durationMs"], reason)
        return unique, meta
