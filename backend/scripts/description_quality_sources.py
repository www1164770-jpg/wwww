"""Read-only record sources for description-quality scripts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = BACKEND_DIR / "frontend"


def load_catalog_records() -> list[dict[str, Any]]:
    module_path = (FRONTEND_DIR / "src" / "data" / "websiteCatalog.js").as_uri()
    script = (
        "import(" + json.dumps(module_path) + ")"
        ".then((module) => process.stdout.write(JSON.stringify(module.websiteCatalog)))"
    )
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=PROJECT_DIR,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    rows = json.loads(result.stdout)
    return [dict(row, website_id=row.get("id")) for row in rows if isinstance(row, dict)]


def load_database_records() -> list[dict[str, Any]]:
    import sys

    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    from db_pool import get_connection, validate_database_config

    validate_database_config()
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW COLUMNS FROM websites")
            website_columns = {row["Field"] for row in cursor.fetchall()}
            filters = []
            if "status" in website_columns:
                filters.append("COALESCE(w.status, 'approved') NOT IN ('deleted', 'disabled')")
            if "enabled" in website_columns:
                filters.append("COALESCE(w.enabled, 1) <> 0")
            status_filter = f"WHERE {' AND '.join(filters)}" if filters else ""
            cursor.execute(
                f"""
                SELECT w.id AS website_id, w.name, w.url, w.description,
                       w.summary, c.name AS category_name,
                       GROUP_CONCAT(DISTINCT t.name ORDER BY t.name SEPARATOR '、') AS tags
                FROM websites w
                LEFT JOIN categories c ON c.id = w.category_id
                LEFT JOIN site_tags st ON st.site_id = w.id
                LEFT JOIN tags t ON t.id = st.tag_id
                {status_filter}
                GROUP BY w.id, w.name, w.url, w.description, w.summary, c.name
                ORDER BY w.id
                """
            )
            return list(cursor.fetchall())
    finally:
        conn.close()


def load_records(source: str) -> list[dict[str, Any]]:
    if source == "catalog":
        return load_catalog_records()
    if source == "database":
        return load_database_records()
    raise ValueError(f"Unsupported source: {source}")
