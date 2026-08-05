import re
import sys
import unittest
from pathlib import Path

import pymysql
from flask import Flask
from flask_jwt_extended import JWTManager


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from v1_routes import register_v1_routes


class SchemaCursor:
    def __init__(self, database):
        self.database = database
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        normalized_sql = " ".join(sql.split())
        self.database.statements.append((normalized_sql, params))
        self.rows = []

        if normalized_sql == "SHOW COLUMNS FROM websites":
            self.rows = [
                {"Field": field}
                for field in (
                    "id",
                    "category_id",
                    "name",
                    "url",
                    "logo_url",
                    "clicks",
                    "status",
                    "source",
                    "description",
                )
            ]
        elif normalized_sql == "SHOW COLUMNS FROM categories":
            self.rows = [{"Field": field} for field in ("id", "name")]
        elif "SELECT setting_value FROM app_settings" in normalized_sql:
            self.rows = []
        elif "FROM websites w" in normalized_sql:
            order_sql = re.search(
                r"ORDER BY (.+?) LIMIT", normalized_sql, flags=re.IGNORECASE
            ).group(1)
            self.database.website_order_clauses.append(order_sql)
            order_terms = [term.strip() for term in order_sql.split(",")]
            if "0 DESC" in order_terms:
                raise pymysql.err.OperationalError(
                    1054, "Unknown column '0' in 'order clause'"
                )
            self.rows = [
                {
                    "id": 1,
                    "category_id": 1,
                    "name": "Example AI",
                    "url": "https://example.com",
                    "logo_url": None,
                    "clicks": 7,
                    "status": "approved",
                    "source": "admin",
                    "description": "Frontend AI resource",
                    "category_name": "AI工具",
                }
            ]
        elif "FROM site_tags" in normalized_sql:
            self.rows = []
        elif "FROM site_occupations" in normalized_sql:
            self.rows = []

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)


class SchemaConnection:
    def __init__(self, database):
        self.database = database

    def cursor(self):
        return SchemaCursor(self.database)

    def commit(self):
        return None

    def close(self):
        return None


class CurrentWebsiteSchema:
    def __init__(self):
        self.statements = []
        self.website_order_clauses = []

    def connect(self):
        return SchemaConnection(self)


class RecommendSortV1Tests(unittest.TestCase):
    def setUp(self):
        self.database = CurrentWebsiteSchema()
        app = Flask(__name__)
        app.config.update(
            JWT_SECRET_KEY="recommend-sort-test-key-at-least-32-bytes",
            PROPAGATE_EXCEPTIONS=False,
            TESTING=False,
        )
        app.logger.disabled = True
        JWTManager(app)
        register_v1_routes(app, self.database.connect)
        self.client = app.test_client()

    def test_hot_sort_uses_clicks_and_id_without_independent_zero_terms(self):
        response = self.client.get(
            "/api/sites/hot?limit=8&exclude_ids=fallback-github,fallback-vue"
        )

        self.assertEqual(response.status_code, 200)
        hot_order = self.database.website_order_clauses[-1]
        order_terms = [term.strip() for term in hot_order.split(",")]
        self.assertNotIn("0 DESC", order_terms)
        self.assertIn("COALESCE(w.clicks, 0) DESC", hot_order)
        self.assertIn("w.id DESC", hot_order)

    def test_recommend_returns_200_when_fallback_ids_are_excluded(self):
        response = self.client.get(
            "/api/sites/recommend?limit=8&exclude_ids=fallback-github,fallback-vue"
        )

        self.assertEqual(response.status_code, 200)
        executed_params = repr([params for _sql, params in self.database.statements])
        self.assertNotIn("fallback-github", executed_params)
        self.assertNotIn("fallback-vue", executed_params)

    def test_canonical_occupation_uses_existing_chinese_career_rule(self):
        response = self.client.get(
            "/api/sites/recommend?occupation=frontend_developer&limit=8&ai_only=1"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["data"])
        self.assertIn("前端开发", payload["data"][0]["reason"])
        self.assertNotIn("工作和创作场景", payload["data"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
