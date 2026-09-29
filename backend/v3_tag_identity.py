"""Rebind approved review records using conservative, reproducible evidence.

Only a unique full resource URL AND matching product name can auto-resolve.
Host/name/redirect/alias similarities remain visible candidates, not approvals.
The source queue is immutable; consumers must revalidate its digest and mapping.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from urllib.parse import urlsplit

from resource_quality import resource_identity
from scripts.summarize_v3_tag_review import summarize

MAPPING_VERSION = "20260925_v3_tag_identity_v1"


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def identity(url):
    try:
        return resource_identity(url)
    except (ValueError, TypeError):
        return None


def name_key(value):
    return " ".join(str(value or "").split()).casefold()


def summary_site(site):
    return {key: site.get(key) for key in ("id", "name", "url", "status", "source")}


def resolve_review_queue(queue, data):
    validation = summarize(queue)
    if not validation["ready_for_migration_preview"]:
        raise ValueError("Source review queue is not fully validated")
    sites = data["websites"]
    by_id = {row["id"]: row for row in sites}
    # Recommendation matching already casefolds tags. Match that identity rule
    # without relying on broader MySQL accent-insensitive collation behavior.
    codes = {tag["id"]: tag["name"].casefold() for tag in data["tags"]}
    existing = {(row["site_id"], codes.get(row["tag_id"])) for row in data["site_tags"]}
    seen = set()
    rows, revised = [], []
    for index, item in enumerate(queue["items"]):
        if item["review_status"] != "approved":
            continue
        key = identity(item["url"])
        exact = [site for site in sites if key and identity(site["url"]) == key]
        names = [site for site in sites if name_key(site["name"]) == name_key(item["website"])]
        host = urlsplit(key).hostname if key else None
        neighbors = [site for site in sites if identity(site["url"]) and urlsplit(identity(site["url"])).hostname == host]
        candidates = exact or names or neighbors
        old = {"id": item["website_id"], "name": item["website"], "url": item["url"]}
        row = {"source_index": index, "source_record_sha256": digest(item), "old": old,
               "approved_tags": list(item["approved_tags"]), "signal": item.get("signal"),
               "candidate_count": len(candidates), "candidates": [summary_site(site) for site in candidates],
               "old_id_current_record": summary_site(by_id[item["website_id"]]) if item["website_id"] in by_id else None,
               "match_basis": [], "status": "unresolved", "target": None}
        target = exact[0] if len(exact) == 1 and name_key(exact[0]["name"]) == name_key(item["website"]) and exact[0].get("status") in (None, "approved", "active") else None
        if target:
            row["target"] = summary_site(target)
            row["match_basis"] = ["unique_complete_normalized_url", "same_product_name", "active_catalog_record"]
            row["conflict_reason"] = "id_changed" if target["id"] != item["website_id"] else "identity_unchanged"
            missing = [code for code in item["approved_tags"] if (target["id"], code) not in existing]
            pending = [code for code in missing if (target["id"], code) not in seen]
            row["existing_tags"] = [code for code in item["approved_tags"] if code not in missing]
            row["new_unique_tags"] = pending
            row["status"] = "no_migration_existing" if not missing else "resolved_pending" if pending else "no_migration_duplicate_review"
            seen.update((target["id"], code) for code in missing)
            updated = deepcopy(item)
            updated.update(website_id=target["id"], website=target["name"], url=target["url"])
            updated["identity_mapping"] = {"source_index": index, "source_record_sha256": digest(item),
                "old": old, "match_basis": row["match_basis"]}
            revised.append(updated)
        else:
            row["conflict_reason"] = ("ambiguous_full_url" if len(exact) > 1 else "name_or_status_changed" if exact
                else "url_or_locale_changed" if names else "different_product_path" if neighbors else "resource_missing")
            row["match_basis"] = ["name_only_not_identity"] if names else ["same_host_different_path_not_identity"] if neighbors else ["no_catalog_candidate"]
        rows.append(row)
    counts = Counter(row["status"] for row in rows)
    reliable = len(revised)
    mapped = {"mode": "mapped_approved_subset", "migration_version": MAPPING_VERSION,
              "source_review_sha256": digest(queue), "algorithm_version": queue.get("algorithm_version"),
              "questionnaire_version": queue.get("questionnaire_version"),
              "profile_schema_version": queue.get("profile_schema_version"),
              "items": revised}
    report = {"version": MAPPING_VERSION, "source_review_sha256": digest(queue),
              "catalog_snapshot_sha256": digest(data), "database_write_performed": False,
              "summary": {"approved_records": len(rows), "reliably_mapped": reliable,
                  "requires_new_associations": counts["resolved_pending"],
                  "no_migration_existing": counts["no_migration_existing"],
                  "no_migration_duplicate_review": counts["no_migration_duplicate_review"],
                  "unresolved": counts["unresolved"], "unique_pending_associations": len(seen),
                  "unique_target_resources": len({r["website_id"] for r in revised})},
              "rows": rows,
              "historical_merge_status": "unknown; shared targets show duplicate review identities, not proof of a historical database merge"}
    report["shared_target_old_ids"] = [{"target_id": target,
        "old_ids": sorted({row["old"]["id"] for row in rows if row["target"] and row["target"]["id"] == target})}
        for target in sorted({row["website_id"] for row in revised})
        if len({row["old"]["id"] for row in rows if row["target"] and row["target"]["id"] == target}) > 1]
    return report, mapped


def validate_mapped_queue(mapped, source_queue, data):
    if source_queue is None or mapped.get("source_review_sha256") != digest(source_queue):
        raise ValueError("Mapped review needs the unchanged original source queue")
    _, expected = resolve_review_queue(source_queue, data)
    if mapped != expected:
        raise ValueError("Mapped review drift/tampering; rebuild the mapping preview")
