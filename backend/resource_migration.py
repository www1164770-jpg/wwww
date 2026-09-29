"""Version 20260924 resource maintenance, with owned changes and reversible links.

No website, favorite, history, or existing tag record is deleted or re-keyed.
Merge records are explicit equivalence links pending a future UI consolidation;
all original IDs remain addressable. Automated evidence never overwrites manual
values: provenance is stored as separate claims, resolved by priority.
"""
import hashlib
import json
import re

from sqlalchemy import (MetaData, Table, Column, Integer, String, Text,
                        UniqueConstraint, select, inspect)
from resource_quality import resource_identity
from scripts.summarize_v3_tag_review import summarize
from resource_fields import effective_fields

VERSION = "20260924_resource_quality_v1"


class ReviewIdentityDrift(ValueError):
    def __init__(self, conflicts):
        super().__init__("Approved review identities differ from the current catalog")
        self.conflicts = conflicts
metadata = MetaData()
journal = Table("resource_quality_changes", metadata,
    Column("id", Integer, primary_key=True),
    Column("version", String(80), nullable=False),
    Column("change_key", String(64), nullable=False),
    Column("kind", String(32), nullable=False),
    Column("payload", Text, nullable=False),
    Column("state", String(16), nullable=False),
    UniqueConstraint("version", "change_key", name="uq_resource_quality_change"),
    mysql_engine="InnoDB", mysql_charset="utf8mb4")
claims = Table("resource_field_claims", metadata,
    Column("id", Integer, primary_key=True),
    Column("site_id", Integer, nullable=False),
    Column("field", String(40), nullable=False),
    Column("value", Text),
    Column("source_kind", String(20), nullable=False),
    Column("source_ref", Text, nullable=False),
    Column("verified_at", String(40)),
    Column("state", String(16), nullable=False), mysql_engine="InnoDB", mysql_charset="utf8mb4")
merges = Table("resource_identity_links", metadata,
    Column("id", Integer, primary_key=True),
    Column("source_id", Integer, nullable=False),
    Column("target_id", Integer, nullable=False),
    Column("evidence", Text, nullable=False),
    Column("state", String(16), nullable=False),
    UniqueConstraint("source_id", name="uq_resource_identity_source"), mysql_engine="InnoDB", mysql_charset="utf8mb4")


def catalog_tables(conn):
    return {name: Table(name, MetaData(), autoload_with=conn)
            for name in ("websites", "tags", "site_tags", "site_occupations")}


def snapshot(conn):
    tables = catalog_tables(conn)
    return {name: [dict(row) for row in conn.execute(select(table).order_by(table.c.id)).mappings()]
            for name, table in tables.items()}


def approved_tag_plan(queue, data, *, source_queue=None):
    if queue.get("mode") == "mapped_approved_subset":
        from v3_tag_identity import validate_mapped_queue
        validate_mapped_queue(queue, source_queue, data)
    summary = summarize(queue)
    if not summary["ready_for_migration_preview"]:
        raise ValueError("Review queue is not ready: " + str(summary["validation_errors"]))
    from scripts.generate_v3_tag_candidates import FIRST_BATCH
    allowed = {tag for group in FIRST_BATCH.values() for tag in group["tags"]}
    sites = {row["id"]: row for row in data["websites"]}
    tags = {}
    for row in data["tags"]:
        code = row["name"].casefold()
        if code in tags and tags[code] != row["id"]:
            raise ValueError(f"Ambiguous case-normalized tag code: {code}")
        tags[code] = row["id"]
    existing = {(row["site_id"], row["tag_id"]) for row in data["site_tags"]}
    conflicts = []
    for item in queue["items"]:
        if item.get("review_status") != "approved":
            continue
        site = sites.get(item.get("website_id"))
        if not site or resource_identity(site["url"]) != resource_identity(item["url"]) or site["name"].strip().casefold() != item["website"].strip().casefold():
            conflicts.append({"review_id": item["website_id"], "review_name": item["website"],
                "review_url": item["url"], "current_record": {key: site[key] for key in ("id", "name", "url")} if site else None,
                "same_url_candidates": [{**{key: candidate[key] for key in ("id", "name", "url")},
                    "approved_codes_already_present": [code for code in item["approved_tags"] if (candidate["id"], tags.get(code)) in existing]}
                    for candidate in sites.values() if resource_identity(candidate["url"]) == resource_identity(item["url"])]})
    if conflicts:
        raise ReviewIdentityDrift(conflicts)
    changes, seen = [], set()
    for item in queue["items"]:
        if item["review_status"] != "approved":
            if item.get("approved_tags"):
                raise ValueError("Unapproved record contains approved tags")
            continue
        sid = item["website_id"]
        site = sites.get(sid)
        if (not site or resource_identity(site["url"]) != resource_identity(item["url"])
                or site["name"].strip().casefold() != item["website"].strip().casefold()):
            raise ValueError(f"Review identity drift: website {sid}")
        if not str(item.get("review_note") or "").strip() or not item.get("candidate_reason"):
            raise ValueError(f"Missing review evidence: website {sid}")
        for tag in item["approved_tags"]:
            if tag not in allowed or not re.fullmatch(r"[a-z][a-z0-9_]*", tag):
                raise ValueError(f"Unknown approved tag code: {tag}")
            if (sid, tag) in seen:
                continue
            seen.add((sid, tag))
            changes.append({"kind": "tag", "site_id": sid, "tag": tag,
                            "already_present": (sid, tags.get(tag)) in existing,
                            "evidence": item["review_note"], "review_url": item["url"]})
            if item.get("identity_mapping"):
                changes[-1]["identity_mapping"] = item["identity_mapping"]
                changes[-1]["source_review_sha256"] = queue["source_review_sha256"]
    return changes


def maintenance_plan(document, data):
    sites = {row["id"]: row for row in data["websites"]}
    changes = []
    # Uses existing summary/description for purpose; is_free remains a legacy
    # boolean, not a verified pricing model. Extraction language is not catalog
    # language, and neither is automatically promoted to verified evidence.
    fields = {"summary", "description", "audience", "pricing_model", "language", "entry_requirements"}
    for item in document:
        row = dict(item)
        if row.get("kind") == "merge":
            if row.get("source_id") == row.get("target_id"):
                raise ValueError("Cannot merge a resource into itself")
            for key in ("source", "target"):
                site = sites.get(row.get(key + "_id"))
                if not site or resource_identity(site["url"]) != resource_identity(row.get(key + "_url", "")):
                    raise ValueError("Merge identity drift")
            if not row.get("evidence") or row.get("reviewed") is not True:
                raise ValueError("Merge needs explicit reviewed evidence")
        elif row.get("kind") == "field":
            site = sites.get(row.get("site_id"))
            if not site or resource_identity(site["url"]) != resource_identity(row.get("url", "")):
                raise ValueError("Field identity drift")
            if row.get("field") not in fields or row.get("source_kind") not in {"manual", "web_extract", "ai_suggestion"}:
                raise ValueError("Unknown field/provenance")
            if not row.get("source_ref"):
                raise ValueError("Field requires provenance")
            if row.get("verified_at"):
                from datetime import datetime
                datetime.fromisoformat(row["verified_at"].replace("Z", "+00:00"))
            if row.get("source_kind") == "ai_suggestion" and row.get("verified_at"):
                raise ValueError("AI suggestions cannot self-verify")
        else:
            raise ValueError("Unknown maintenance kind")
        changes.append(row)
    return changes


def change_key(change):
    content = {key: value for key, value in change.items() if key != "already_present"}
    return hashlib.sha256(json.dumps(content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def apply_plan(conn, changes, *, version=VERSION):
    tables = catalog_tables(conn)
    applied = []
    for change in changes:
        key = change_key(change)
        previous = conn.execute(select(journal).where(journal.c.version == version, journal.c.change_key == key)).mappings().first()
        if previous and previous["state"] == "active":
            continue
        kind = change["kind"]
        payload = dict(change)
        if kind == "tag":
            tags, links = tables["tags"], tables["site_tags"]
            existing_tag = conn.execute(select(tags.c.id, tags.c.name).where(tags.c.name == change["tag"])).first()
            if existing_tag and existing_tag.name.casefold() != change["tag"].casefold():
                raise ValueError("Tag collation collision; refusing to reuse a different code")
            tid = existing_tag.id if existing_tag else None
            if tid is None:
                tid = conn.execute(tags.insert().values(name=change["tag"], type="general")).inserted_primary_key[0]
            existing = conn.execute(select(links.c.id).where(links.c.site_id == change["site_id"], links.c.tag_id == tid)).first()
            if existing:
                continue
            payload["owned_id"] = conn.execute(links.insert().values(site_id=change["site_id"], tag_id=tid)).inserted_primary_key[0]
            payload["tag_id"] = tid
        elif kind == "field":
            payload["owned_id"] = conn.execute(claims.insert().values(
                **{key: change.get(key) for key in ("site_id", "field", "value", "source_kind", "source_ref", "verified_at")},
                state="active")).inserted_primary_key[0]
        elif kind == "merge":
            active = list(conn.execute(select(merges).where(merges.c.state == "active")).mappings())
            # No chains or cycles; all references stay attached to their source.
            if any(change["source_id"] in (r["source_id"], r["target_id"]) or change["target_id"] == r["source_id"] for r in active):
                raise ValueError("Merge conflict/chain; review existing equivalence links")
            old = conn.execute(select(merges).where(merges.c.source_id == change["source_id"])).mappings().first()
            values = {key: change[key] for key in ("source_id", "target_id", "evidence")}
            if old:
                conn.execute(merges.update().where(merges.c.id == old["id"]).values(**values, state="active"))
                payload["owned_id"] = old["id"]
            else:
                payload["owned_id"] = conn.execute(merges.insert().values(**values, state="active")).inserted_primary_key[0]
        else:
            raise ValueError("Unknown migration operation")
        values = dict(version=version, change_key=key, kind=kind,
                      payload=json.dumps(payload, ensure_ascii=False), state="active")
        if previous:
            conn.execute(journal.update().where(journal.c.id == previous["id"]).values(**values))
        else:
            conn.execute(journal.insert().values(**values))
        applied.append(payload)
    return applied


def rollback_plan(conn, *, version=VERSION):
    if not inspect(conn).has_table(journal.name):
        return []
    return [dict(row) for row in conn.execute(select(journal).where(
        journal.c.version == version, journal.c.state == "active").order_by(journal.c.id.desc())).mappings()]


def rollback(conn, *, version=VERSION):
    tables = catalog_tables(conn)
    rows = rollback_plan(conn, version=version)
    for row in rows:
        payload = json.loads(row["payload"])
        if row["kind"] == "tag":
            links = tables["site_tags"]
            conn.execute(links.delete().where(links.c.id == payload["owned_id"],
                links.c.site_id == payload["site_id"], links.c.tag_id == payload["tag_id"]))
        else:
            table = claims if row["kind"] == "field" else merges
            conn.execute(table.update().where(table.c.id == payload["owned_id"]).values(state="reverted"))
        conn.execute(journal.update().where(journal.c.id == row["id"]).values(state="reverted"))
    # Tag dictionary rows and journals are intentionally retained for provenance.
    return rows
