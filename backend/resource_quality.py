"""Conservative catalog identities and reproducible, read-only quality analysis."""
from collections import Counter, defaultdict
from urllib.parse import urlsplit, urlunsplit

from backend.crawler.net.url import normalize_http_url, InvalidUrl
from career_catalog import CAREERS


def resource_identity(url):
    """Reuse crawler validation/host handling, retaining product-significant bytes.

    Fetch normalization removes fragments, tracking parameters, duplicate slashes
    and sorts queries. Those operations are unsafe for catalog identities (SPA
    routes, signed URLs, ordered parameters), so retain the original components.
    No www, scheme, path-case or trailing-slash alias is inferred.
    """
    normalized = normalize_http_url(url)
    original = urlsplit(url.strip())
    authority = urlsplit(normalized.url).netloc
    return urlunsplit((normalized.scheme, authority, original.path or "/",
                       original.query, original.fragment))


def audit_resources(sites, links, tags, occupations):
    by_id = {row["id"]: row for row in sites}
    tag_ids = {row["id"] for row in tags}
    groups = {key: defaultdict(list) for key in ("url", "name", "description", "fetch_url")}
    invalid = []
    for site in sites:
        for field in ("name", "description"):
            value = " ".join(str(site.get(field) or "").split()).casefold()
            if value:
                groups[field][value].append(site["id"])
        try:
            groups["url"][resource_identity(site["url"])].append(site["id"])
            groups["fetch_url"][normalize_http_url(site["url"]).url].append(site["id"])
        except (InvalidUrl, ValueError, TypeError):
            invalid.append(site["id"])
    tagged = {row["site_id"] for row in links if row["tag_id"] in tag_ids}
    pairs = Counter((row["site_id"], row["tag_id"]) for row in links)
    career_sites = defaultdict(set)
    for row in occupations:
        if row["site_id"] in by_id:
            career_sites[row["occupation"]].add(row["site_id"])
    return {
        "total_resources": len(sites),
        "status_counts": dict(Counter(row.get("status") or "unknown" for row in sites)),
        "empty_fields": {field: sum(row.get(field) is None or str(row.get(field)).strip() == "" for row in sites)
                         for field in sorted({key for row in sites for key in row})},
        "unknown_structured_fields": ["audience", "pricing_model", "language", "entry_requirements", "verified_at"],
        "invalid_url_ids": invalid,
        "duplicate_urls": [ids for ids in groups["url"].values() if len(ids) > 1],
        "same_name_candidates": [ids for ids in groups["name"].values() if len(ids) > 1],
        "fetch_equivalence_candidates": [ids for ids in groups["fetch_url"].values() if len(ids) > 1],
        "duplicate_descriptions": [ids for ids in groups["description"].values() if len(ids) > 1],
        "tagged_resources": len(tagged & by_id.keys()),
        "tag_coverage": [{"code": row["name"], "resource_count": len({link["site_id"] for link in links if link["tag_id"] == row["id"] and link["site_id"] in by_id})} for row in tags],
        "untagged_resource_ids": sorted(by_id.keys() - tagged),
        "duplicate_tag_links": [{"site_id": pair[0], "tag_id": pair[1], "count": count}
                                for pair, count in sorted(pairs.items()) if count > 1],
        "orphan_tag_links": [dict(row) for row in links if row["site_id"] not in by_id or row["tag_id"] not in tag_ids],
        "career_coverage": [{"code": career["code"], "name": career["name"],
                             "persisted_resource_count": len(career_sites[career["code"]]),
                             "approved_resource_count": sum(by_id[sid].get("status") in (None, "approved")
                                                            for sid in career_sites[career["code"]])}
                            for career in CAREERS],
        "candidate_policy": "Candidates only; never merge by domain/name/fetch identity. No redirects fetched.",
    }
