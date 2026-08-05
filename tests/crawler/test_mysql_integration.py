from __future__ import annotations

import os
import unittest

from sqlalchemy import create_engine, text

from backend.crawler.db.migration import validate_migration_target


MYSQL_TEST_URL = os.environ.get("CRAWLER_TEST_DATABASE_URL", "").strip()


@unittest.skipUnless(
    MYSQL_TEST_URL,
    "CRAWLER_TEST_DATABASE_URL is not configured; MySQL integration skipped",
)
class ExplicitMySQLIntegrationTests(unittest.TestCase):
    def test_explicit_test_database_is_safe_and_reachable(self) -> None:
        database_name = validate_migration_target(MYSQL_TEST_URL)
        self.assertIn("test", database_name.lower())

        engine = create_engine(MYSQL_TEST_URL, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                self.assertEqual(connection.execute(text("SELECT 1")).scalar_one(), 1)
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
