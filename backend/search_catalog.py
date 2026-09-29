"""Read current public resource fields and the transactional catalog version."""
import os
from collections import defaultdict
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL


def engine_from_environment():
    from db_pool import validate_database_config
    cfg = validate_database_config()
    return create_engine(URL.create("mysql+pymysql", username=cfg["user"], password=cfg["password"],
        host=cfg["host"], port=cfg["port"], database=cfg["database"]),
        pool_pre_ping=True, isolation_level="READ COMMITTED")


class Catalog:
    def __init__(self, engine):
        self.engine = engine

    def snapshot(self, connection=None):
        if connection is None:
            with self.engine.connect() as conn:
                if self.engine.dialect.name == "mysql":
                    conn.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                    conn.exec_driver_sql("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
                return self.snapshot(conn)
        conn = connection
        tables = set(inspect(conn).get_table_names())
        revision = indexed = None
        if "search_sync_state" in tables:
            state = conn.execute(text("SELECT revision,indexed_revision FROM search_sync_state WHERE id=1")).mappings().one()
            revision, indexed = state["revision"], state["indexed_revision"]
        rows = [dict(r) for r in conn.execute(text("SELECT * FROM websites ORDER BY id")).mappings()]
        categories = {r["id"]: dict(r) for r in conn.execute(text("SELECT * FROM categories")).mappings()} if "categories" in tables else {}
        tags, occupations = defaultdict(list), defaultdict(list)
        if {"tags", "site_tags"} <= tables:
            for row in conn.execute(text("SELECT st.site_id,t.name FROM site_tags st JOIN tags t ON t.id=st.tag_id ORDER BY t.name")).mappings():
                tags[row["site_id"]].append(row["name"])
        if "site_occupations" in tables:
            for row in conn.execute(text("SELECT site_id,occupation FROM site_occupations ORDER BY occupation")).mappings():
                occupations[row["site_id"]].append(row["occupation"])
        for row in rows:
            category = categories.get(row.get("category_id"), {})
            row.update(tags=sorted(set(tags[row["id"]])), occupations=sorted(set(occupations[row["id"]])),
                       category_name=category.get("name"), category_code=category.get("code"))
            row.setdefault("click_count", row.get("clicks") or 0)
            row.setdefault("enabled", 1)
            # No status column means legacy/unreviewed, not implicitly public.
            row.setdefault("status", "unknown")
        if "resource_field_claims" in tables:
            from resource_fields import enrich_resources
            claims=[dict(r) for r in conn.execute(text("SELECT * FROM resource_field_claims WHERE state='active'")).mappings()]
            enrich_resources(rows,claims)
        if "resource_identity_links" in tables:
            links={r["source_id"]:r["target_id"] for r in conn.execute(text("SELECT source_id,target_id FROM resource_identity_links WHERE state='active'")).mappings()}
            for row in rows:
                target=row["id"]; seen=set()
                while target in links and target not in seen:
                    seen.add(target); target=links[target]
                row["canonical_site_id"]=target if target not in seen else row["id"]
        return revision, indexed, rows


def configured_service():
    from search_service import Meili, SearchService, SearchConfigurationError
    mode = os.getenv("SEARCH_BACKEND", "meilisearch")
    if mode not in ("meilisearch", "database"):
        raise SearchConfigurationError("SEARCH_BACKEND must be meilisearch or database")
    meili = Meili(os.getenv("MEILI_HOST", "http://127.0.0.1:7700"), os.getenv("MEILI_MASTER_KEY"), os.getenv("MEILI_INDEX", "websites")) if mode == "meilisearch" else None
    cache = None
    if os.getenv("REDIS_URL"):
        import redis
        cache = redis.Redis.from_url(os.environ["REDIS_URL"], socket_connect_timeout=.3, socket_timeout=.3)
    return SearchService(Catalog(engine_from_environment()), meili, cache)
