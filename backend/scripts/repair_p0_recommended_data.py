"""Idempotently repair P0 recommendation content in an existing database.

Run with ``python backend/scripts/repair_p0_recommended_data.py --apply``.
Without ``--apply`` the script only reports the rows that would change.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from db_pool import get_connection  # noqa: E402
from init_db import COMMON_RECOMMENDED_SITES  # noqa: E402


INVALID_SITE_NAMES = ("学而思", "平安好医生", "好大夫在线")
RECOMMENDATION_CATEGORY_NAMES = ("常用推荐", "AI工具", "开发社区", "编程开发")


def table_columns(cursor, table_name):
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
    return {row["Field"] for row in cursor.fetchall()}


def count_rows(cursor, sql, params):
    cursor.execute(sql, params)
    row = cursor.fetchone() or {}
    return int(row.get("count", 0))


def repair(cursor, apply):
    website_columns = table_columns(cursor, "websites")
    category_columns = table_columns(cursor, "categories")
    if "name" not in category_columns or "name" not in website_columns:
        raise RuntimeError("websites and categories tables must both provide a name column")

    category_marks = ", ".join(["%s"] * len(RECOMMENDATION_CATEGORY_NAMES))
    invalid_marks = ", ".join(["%s"] * len(INVALID_SITE_NAMES))
    invalid_params = (*RECOMMENDATION_CATEGORY_NAMES, *INVALID_SITE_NAMES)
    invalid_where = f"""
        FROM websites w
        INNER JOIN categories c ON c.id = w.category_id
        WHERE c.name IN ({category_marks})
          AND w.name IN ({invalid_marks})
    """
    invalid_count = count_rows(
        cursor,
        f"SELECT COUNT(*) AS count {invalid_where}",
        invalid_params,
    )
    active_invalid_count = invalid_count
    if "status" in website_columns:
        active_invalid_count = count_rows(
            cursor,
            f"SELECT COUNT(*) AS count {invalid_where} AND COALESCE(w.status, 'approved') <> 'disabled'",
            invalid_params,
        )

    disabled_count = 0
    if invalid_count and apply:
        if "status" not in website_columns:
            raise RuntimeError(
                "Refusing to remove recommendation rows because websites.status is unavailable."
            )
        cursor.execute(
            f"""
            UPDATE websites w
            INNER JOIN categories c ON c.id = w.category_id
            SET w.status = 'disabled'
            WHERE c.name IN ({category_marks})
              AND w.name IN ({invalid_marks})
              AND COALESCE(w.status, 'approved') <> 'disabled'
            """,
            invalid_params,
        )
        disabled_count = cursor.rowcount

    description_updates = 0
    description_columns = {"summary", "description"}.intersection(website_columns)
    if description_columns:
        for site in COMMON_RECOMMENDED_SITES:
            assignments = []
            params = []
            for column, value in (
                ("summary", site["summary"]),
                ("description", site["description"]),
            ):
                if column not in description_columns:
                    continue
                assignments.append(
                    f"{column} = CASE WHEN TRIM(COALESCE({column}, '')) IN ('', '高效能 AI 工具') THEN %s ELSE {column} END"
                )
                params.append(value)
            if not assignments:
                continue
            sql = f"UPDATE websites SET {', '.join(assignments)} WHERE name = %s"
            if apply:
                cursor.execute(sql, (*params, site["name"]))
                description_updates += cursor.rowcount
            else:
                description_updates += count_rows(
                    cursor,
                    """
                    SELECT COUNT(*) AS count FROM websites
                    WHERE name = %s
                      AND (TRIM(COALESCE(summary, '')) IN ('', '高效能 AI 工具')
                           OR TRIM(COALESCE(description, '')) IN ('', '高效能 AI 工具'))
                    """,
                    (site["name"],),
                )

    return {
        "invalid_matches": invalid_count,
        "active_invalid_matches": active_invalid_count,
        "disabled": disabled_count,
        "description_updates": description_updates,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write the targeted repair")
    args = parser.parse_args()

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            result = repair(cursor, args.apply)
        if args.apply:
            connection.commit()
        else:
            connection.rollback()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    mode = "APPLIED" if args.apply else "DRY RUN"
    print(f"{mode}: invalid recommendation rows matched: {result['invalid_matches']}")
    print(f"{mode}: active invalid recommendation rows: {result['active_invalid_matches']}")
    print(f"{mode}: rows disabled: {result['disabled']}")
    print(f"{mode}: description fields backfilled: {result['description_updates']}")


if __name__ == "__main__":
    main()
