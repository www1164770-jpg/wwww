import sys
import unittest
from pathlib import Path

from flask import Flask
from flask_jwt_extended import JWTManager

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from v1_routes import (  # noqa: E402
    normalize_search_query,
    rank_search_sites,
    search_term_groups,
    register_v1_routes,
)


class SearchCursor:
    def __init__(self, database):
        self.database = database
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        self.database.statements.append((normalized, params))
        self.rows = []
        if normalized == "SHOW COLUMNS FROM websites":
            self.rows = [{"Field": field} for field in self.database.website_columns]
        elif normalized == "SHOW COLUMNS FROM categories":
            self.rows = [{"Field": field} for field in self.database.category_columns]
        elif normalized == "SHOW COLUMNS FROM site_tags":
            self.rows = [{"Field": "site_id"}, {"Field": "tag_id"}]
        elif normalized == "SHOW COLUMNS FROM tags":
            self.rows = [{"Field": "id"}, {"Field": "name"}]
        elif normalized == "SHOW COLUMNS FROM site_occupations":
            self.rows = [{"Field": "site_id"}, {"Field": "occupation"}]
        elif normalized.startswith("SELECT id, name,") and "FROM categories" in normalized:
            self.rows = [
                {"id": 10, "name": "框架文档", "code": "framework_docs"},
                {"id": 11, "name": "UI 组件库", "code": "ui_components"},
            ]
        elif "FROM categories" in normalized and "ORDER BY" in normalized:
            self.rows = [
                {"id": 10, "name": "框架文档", "code": "framework_docs"},
                {"id": 11, "name": "UI 组件库", "code": "ui_components"},
            ]
        elif normalized.startswith("SELECT w.*"):
            self.database.search_query_count += 1
            self.rows = [
                dict(site)
                for site in self.database.sites
                if site.get("enabled", 1) == 1
                and site.get("status", "approved") in {"approved", "active"}
            ]

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)


class SearchConnection:
    def __init__(self, database):
        self.database = database

    def cursor(self):
        return SearchCursor(self.database)

    def close(self):
        return None


class SearchDatabase:
    website_columns = {
        "id",
        "category_id",
        "name",
        "url",
        "logo_url",
        "summary",
        "description",
        "aliases",
        "use_cases",
        "enabled",
        "status",
        "recommend_level",
        "quality_score",
        "click_count",
        "updated_at",
    }
    category_columns = {"id", "name", "code", "status", "sort_order"}

    def __init__(self):
        self.statements = []
        self.search_query_count = 0
        self.sites = [
            {
                "id": 1,
                "category_id": 10,
                "name": "Vue.js",
                "url": "https://vuejs.org/",
                "summary": "渐进式 JavaScript 前端框架",
                "description": "用于构建用户界面",
                "category_name": "框架文档",
                "category_code": "framework_docs",
                "tags_text": "Vue|||JavaScript",
                "occupations_text": "前端开发",
                "aliases": "vue framework",
                "use_cases": "前端框架",
                "enabled": 1,
                "status": "approved",
                "recommend_level": 8,
                "quality_score": 90,
                "click_count": 100,
                "updated_at": "2026-08-01",
            },
            {
                "id": 2,
                "category_id": 10,
                "name": "Vuetify",
                "url": "https://vuetifyjs.com/",
                "summary": "Vue UI 组件库",
                "description": "Material Design components",
                "category_name": "UI 组件库",
                "category_code": "ui_components",
                "tags_text": "Vue|||组件库",
                "occupations_text": "前端开发",
                "aliases": "vue components",
                "use_cases": "UI 组件库",
                "enabled": 1,
                "status": "approved",
                "recommend_level": 6,
                "quality_score": 80,
                "click_count": 80,
                "updated_at": "2026-07-01",
            },
            {
                "id": 3,
                "category_id": 10,
                "name": "Hidden Vue",
                "url": "https://hidden.example/",
                "summary": "不应返回",
                "description": "未启用",
                "category_name": "框架文档",
                "category_code": "framework_docs",
                "tags_text": "Vue",
                "occupations_text": "前端开发",
                "aliases": "",
                "use_cases": "",
                "enabled": 0,
                "status": "approved",
                "recommend_level": 10,
                "quality_score": 100,
                "click_count": 1000,
                "updated_at": "2026-08-02",
            },
            {
                "id": 4,
                "category_id": 10,
                "name": "Vue 官方镜像",
                "url": "https://vuejs.org/",
                "summary": "重复 URL",
                "description": "不应重复",
                "category_name": "框架文档",
                "category_code": "framework_docs",
                "tags_text": "Vue",
                "occupations_text": "前端开发",
                "aliases": "",
                "use_cases": "",
                "enabled": 1,
                "status": "approved",
                "recommend_level": 1,
                "quality_score": 10,
                "click_count": 1,
                "updated_at": "2026-08-03",
            },
        ]

    def connect(self):
        return SearchConnection(self)


class SiteSearchV1Tests(unittest.TestCase):
    def setUp(self):
        self.database = SearchDatabase()
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            JWT_SECRET_KEY="site-search-v1-test-secret-key-long-enough",
        )
        JWTManager(self.app)
        register_v1_routes(self.app, self.database.connect)
        self.client = self.app.test_client()

    def test_normalizes_whitespace_and_keeps_chinese_phrase(self):
        self.assertEqual(normalize_search_query("  AI   编程  "), "AI 编程")
        self.assertEqual(search_term_groups("前端框架"), [("前端框架", "vue", "react", "angular", "svelte", "nuxt", "前端", "框架")])

    def test_exact_name_ranks_before_related_name(self):
        ranked = rank_search_sites(self.database.sites[:2], "Vue")
        self.assertEqual(ranked[0]["name"], "Vue.js")
        self.assertIn("name", ranked[0]["matchedFields"])

    def test_search_returns_pagination_and_deduplicates_url(self):
        response = self.client.get("/api/sites/search?q=Vue&page=1&page_size=2")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()["data"]
        self.assertEqual(payload["pagination"]["pageSize"], 2)
        self.assertEqual(payload["pagination"]["total"], 2)
        self.assertEqual(len(payload["items"]), 2)
        self.assertEqual(len({item["url"] for item in payload["items"]}), 2)

    def test_search_empty_result_is_successful(self):
        self.database.sites = []
        response = self.client.get("/api/search?q=missingxyz987")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()["data"]
        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["pagination"]["total"], 0)

    def test_requested_search_terms_return_valid_json(self):
        for query in ("论文写作", "AI编程", "PPT", "设计", "Python"):
            with self.subTest(query=query):
                response = self.client.get("/api/search", query_string={"q": query})
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()["data"]
                self.assertIsInstance(payload["items"], list)
                self.assertIn("total", payload["pagination"])

    def test_categories_returns_current_database_shape(self):
        response = self.client.get("/api/categories")
        self.assertEqual(response.status_code, 200)
        categories = response.get_json()["data"]
        self.assertTrue(categories)
        self.assertIn("code", categories[0])

    def test_search_cache_avoids_second_database_search(self):
        first = self.client.get("/api/search?q=Vue")
        second = self.client.get("/api/search?q=Vue")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(first.get_json()["data"]["cached"])
        self.assertTrue(second.get_json()["data"]["cached"])
        self.assertEqual(self.database.search_query_count, 1)

    def test_search_validation_is_explicit(self):
        self.assertEqual(self.client.get("/api/sites/search").status_code, 400)
        self.assertEqual(
            self.client.get("/api/sites/search?q=x&sort=unsafe").status_code,
            400,
        )
        self.assertEqual(
            self.client.get("/api/sites/search?q=x&page=0").status_code,
            400,
        )
        self.assertEqual(
            self.client.get("/api/sites/search?q=" + "x" * 101).status_code,
            400,
        )

    def test_page_size_is_capped_and_category_resolves(self):
        response = self.client.get(
            "/api/sites/search?q=Vue&category=framework_docs&page_size=200"
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()["data"]
        self.assertEqual(payload["pagination"]["pageSize"], 50)
        self.assertEqual(payload["category"]["code"], "framework_docs")

    def test_suggestions_are_structured_and_limited(self):
        response = self.client.get("/api/sites/search/suggest?q=Vue")
        self.assertEqual(response.status_code, 200)
        items = response.get_json()["data"]["items"]
        self.assertLessEqual(len(items), 8)
        self.assertTrue(all(item["type"] in {"site", "category", "keyword"} for item in items))

    def test_development_rate_limiter_has_no_redis_delay(self):
        source = (BACKEND_DIR / "app.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("limiter = Limiter("), 1)
        self.assertIn('return "memory://"', source)


if __name__ == "__main__":
    unittest.main()
