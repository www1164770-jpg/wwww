"""Prepare only a brand-new Docker database, then use the normal app entry."""

import os
import sys

from db_pool import get_database_config, validate_database_config
import pymysql


def main():
    # Compose waits for authenticated MySQL readiness before starting us.
    # Never seed or migrate an existing database here.
    config = validate_database_config(get_database_config())
    with pymysql.connect(**config) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            empty_database = not cursor.fetchone()

    if empty_database:
        from app import initialize_database
        from init_db import run

        initialize_database()
        # The existing standalone importer commits categories before websites.
        # It avoids the pooled startup sync's rollback on an empty database.
        run()

    os.execv(sys.executable, [sys.executable, "backend/app.py"])


if __name__ == "__main__":
    main()
