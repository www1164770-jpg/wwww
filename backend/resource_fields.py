"""Read-only projection of evidence; AI suggestions stay unpublished."""


def effective_fields(rows):
    result = {}
    for row in sorted(rows, key=lambda r: (r["source_kind"] == "manual", r["id"])):
        if row["state"] == "active" and row["source_kind"] != "ai_suggestion":
            result[row["field"]] = {key: row.get(key) for key in
                                    ("value", "source_kind", "source_ref", "verified_at")}
    return result


def enrich_resources(sites, rows):
    """Reuse summary/description; extraction cannot replace populated legacy copy."""
    for site in sites:
        fields = effective_fields([row for row in rows if row["site_id"] == site["id"]])
        site["resource_metadata"] = fields
        for field, evidence in fields.items():
            if field in {"summary", "description"}:
                if evidence["source_kind"] == "manual" or not site.get(field):
                    site[field] = evidence["value"]
            else:
                site[field] = evidence["value"]
    return sites
