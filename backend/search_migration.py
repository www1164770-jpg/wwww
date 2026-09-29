"""Versioned MySQL transactional change capture into the EXISTING outbox model.

No migration runs during imports/application startup. Triggers cover direct SQL,
ORM, imports and cascade roots, without a second event queue.
"""
from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateTable
from backend.crawler.db import OutboxEvent

VERSION = "20260925_search_sync_v1"
TABLES = ("websites", "site_tags", "tags", "site_occupations", "categories", "resource_field_claims", "resource_identity_links")
STATE_SQL = """CREATE TABLE IF NOT EXISTS search_sync_state (
id INTEGER PRIMARY KEY, revision BIGINT NOT NULL DEFAULT 0,
indexed_revision BIGINT NOT NULL DEFAULT -1,
task_id BIGINT NULL, task_kind VARCHAR(32) NULL,
target_index VARCHAR(128) NULL, updated_at DATETIME(6) NULL
) ENGINE=InnoDB"""


def preview(conn):
    tables = set(inspect(conn).get_table_names())
    existing = {r[0] for r in conn.execute(text("SELECT TRIGGER_NAME FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE()"))}
    statements = [STATE_SQL, "INSERT IGNORE INTO search_sync_state(id,revision,indexed_revision) VALUES(1,0,-1)"]
    for table in TABLES:
        if table not in tables:
            continue
        for event in ("INSERT", "UPDATE", "DELETE"):
            name = f"search_v2_{table}_{event.lower()}"
            if name in existing:
                continue
            statements.append(f"""CREATE TRIGGER `{name}` AFTER {event} ON `{table}` FOR EACH ROW
BEGIN
 UPDATE search_sync_state SET revision=revision+1,updated_at=UTC_TIMESTAMP(6) WHERE id=1;
 INSERT INTO outbox_events(event_uid,aggregate_type,aggregate_uid,event_type,payload_json,status,attempt_count,max_attempts,available_at,created_at,updated_at)
 VALUES(UUID(),'search_catalog','public','search.changed',JSON_OBJECT('table','{table}','operation','{event}'),'pending',0,5,UTC_TIMESTAMP(),UTC_TIMESTAMP(6),UTC_TIMESTAMP(6));
END""")
    engines = {r[0]: r[1] for r in conn.execute(text("SELECT TABLE_NAME,ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE()"))}
    unsafe = [t for t in set(TABLES).intersection(tables) | ({"outbox_events", "search_sync_state"} & tables) if engines.get(t) != "InnoDB"]
    if unsafe:
        raise ValueError("Transactional search capture requires InnoDB: " + ",".join(unsafe))
    return {"version": VERSION, "database": conn.engine.url.database, "outbox_table": str(CreateTable(OutboxEvent.__table__, if_not_exists=True).compile(conn)), "statements": statements,
            "covered_tables": sorted(tables.intersection(TABLES)), "missing_optional_tables": sorted(set(TABLES)-tables),
            "rollback": [f"DROP TRIGGER IF EXISTS `search_v2_{t}_{event}`" for t in TABLES for event in ("insert", "update", "delete")] + (["UPDATE search_sync_state SET indexed_revision=-1 WHERE id=1"] if "search_sync_state" in tables else []),
            "rollback_policy": "Stop worker; select SEARCH_BACKEND=database; remove only these triggers. Retain all business data, versions and outbox audit records."}


def apply(conn, reviewed):
    current = preview(conn)
    if current != reviewed:
        raise ValueError("Migration preview drift; inspect a fresh preview")
    OutboxEvent.__table__.create(conn, checkfirst=True)
    for sql in current["statements"]:
        conn.exec_driver_sql(sql)
    conn.commit()
