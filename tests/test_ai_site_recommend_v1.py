import inspect
import sys
import unittest
from pathlib import Path

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai_site_recommend_service import (
    normalize_string_list,
    normalize_text,
    recommend_sites_for_query,
)
from v1_routes import register_v1_routes


def site(site_id, name, url, **fields):
    return {
        "id": site_id,
        "name": name,
        "url": url,
        "logo_url": fields.get("logo_url", ""),
        "summary": fields.get("summary", ""),
        "description": fields.get("description", ""),
        "category_name": fields.get("category_name", ""),
        "tags": fields.get("tags", []),
        "occupations": fields.get("occupations", []),
        "quality_score": fields.get("quality_score", 0),
        "favorite_count": fields.get("favorite_count", 0),
        "click_count": fields.get("click_count", fields.get("clicks", 0)),
        "clicks": fields.get("clicks", 0),
        "rating_avg": fields.get("rating_avg", 0),
        "status": fields.get("status", "approved"),
    }


class FakeCursor:
    def __init__(self, database):
        self.database = database
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, _params=None):
        normalized = " ".join(sql.split())
        self.rows = []
        if normalized == "SHOW COLUMNS FROM websites":
            self.rows = [
                {"Field": field}
                for field in (
                    "id", "category_id", "name", "url", "logo_url", "summary",
                    "description", "quality_score", "favorite_count", "click_count",
                    "clicks", "rating_avg", "status", "created_at",
                )
            ]
        elif normalized == "SHOW COLUMNS FROM categories":
            self.rows = [{"Field": "id"}, {"Field": "name"}]
        elif "SELECT * FROM users WHERE username=%s OR email=%s" in normalized:
            self.rows = [{"id": 7, "username": "member", "email": "member@example.test"}]
        elif "SELECT occupation, interests FROM user_profiles" in normalized:
            self.rows = [self.database.profile]
        elif "FROM websites w" in normalized:
            limit = int(_params[-2])
            self.database.site_query_limits.append(limit)
            self.rows = [dict(item) for item in self.database.candidates[:limit]]
        elif "FROM site_tags" in normalized or "FROM site_occupations" in normalized:
            self.rows = []

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)


class FakeConnection:
    def __init__(self, database):
        self.database = database

    def cursor(self):
        return FakeCursor(self.database)

    def close(self):
        return None


class FakeDatabase:
    def __init__(self, candidates=None, profile=None):
        self.candidates = candidates or []
        self.profile = profile or {"occupation": "", "interests": "[]"}
        self.site_query_limits = []

    def connect(self):
        return FakeConnection(self)


class LocalMatcherTests(unittest.TestCase):
    def test_normalizers_strip_html_and_parse_safe_lists(self):
        self.assertEqual(normalize_text("<b>Python</b>  DEBUG"), "python debug")
        self.assertEqual(normalize_string_list('["编程", "调试"]'), ["编程", "调试"])
        self.assertEqual(normalize_string_list("编程，调试; Python"), ["编程", "调试", "Python"])

    def test_name_match_outranks_description_only_match(self):
        results = recommend_sites_for_query(
            "Python 调试",
            [
                site(1, "Python 调试工具", "https://name.example"),
                site(2, "通用工具", "https://description.example", description="适合 Python 调试"),
            ],
        )
        self.assertEqual([item["site"]["id"] for item in results], [1, 2])

    def test_tags_category_and_occupation_produce_reasons(self):
        results = recommend_sites_for_query(
            "代码调试",
            [site(1, "工具", "https://match.example", tags='["编程", "调试"]', category_name="编程开发", occupations=["程序员"])],
            occupation="程序员",
            interests=["编程"],
        )
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["reason"])
        self.assertGreater(results[0]["score"], 0)

    def test_invalid_candidates_duplicates_and_irrelevant_sites_are_filtered(self):
        results = recommend_sites_for_query(
            "Python 调试",
            [
                site(1, "Python 调试", "https://valid.example"),
                site(1, "Python 调试重复", "https://duplicate-id.example"),
                site(3, "Python 调试重复 URL", "https://valid.example"),
                site(4, "Python 调试", "javascript:alert(1)"),
                site(5, "Python 调试", "https://pending.example", status="pending"),
                site(6, "热门新闻", "https://irrelevant.example", quality_score=100, click_count=999999),
            ],
            limit=100,
        )
        self.assertEqual([item["site"]["id"] for item in results], [1])

    def test_profile_occupation_breaks_similar_text_match_ties_and_limit_is_five(self):
        candidates = [
            site(1, "数据分析工具", "https://analyst.example", occupations=["数据分析师"]),
            site(2, "数据分析工具", "https://other.example", occupations=["设计师"]),
        ] + [
            site(index, f"数据分析工具 {index}", f"https://{index}.example")
            for index in range(3, 10)
        ]
        results = recommend_sites_for_query("数据分析工具", candidates, occupation="数据分析师", limit=100)
        self.assertEqual(results[0]["site"]["id"], 1)
        self.assertLessEqual(len(results), 5)

    def test_service_has_no_external_ai_dependencies(self):
        import ai_site_recommend_service as service

        source = inspect.getsource(service)
        for forbidden in ("requests", "OpenAI", "DeepSeek", "ai_server", "os.getenv"):
            self.assertNotIn(forbidden, source)


class AiSiteRecommendRouteTests(unittest.TestCase):
    def setUp(self):
        self.database = FakeDatabase(
            candidates=[
                site(1, "Python 调试工具", "https://python-debug.example", summary="帮助定位代码错误"),
                site(2, "无效状态", "https://pending.example", summary="Python 调试", status="pending"),
                site(3, "无效地址", "javascript:alert(1)", summary="Python 调试"),
            ],
            profile={"occupation": "程序员", "interests": '["编程"]'},
        )
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, JWT_SECRET_KEY="ai-site-recommend-test-key")
        JWTManager(self.app)
        register_v1_routes(self.app, self.database.connect)
        self.client = self.app.test_client()

    def headers(self):
        with self.app.app_context():
            token = create_access_token(identity="member")
        return {"Authorization": f"Bearer {token}"}

    def test_route_requires_login(self):
        self.assertEqual(self.client.post("/api/ai/site-recommend", json={"query": "Python 调试"}).status_code, 401)

    def test_route_validates_query(self):
        invalid_payloads = [{}, {"query": None}, {"query": 123}, {"query": "   "}, {"query": "编"}, {"query": "x" * 501}]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post("/api/ai/site-recommend", json=payload, headers=self.headers())
                self.assertEqual(response.status_code, 400)
                self.assertEqual(set(response.get_json()), {"code", "legacy_code", "message", "msg", "data"})

    def test_route_returns_only_real_valid_sites_and_strips_html_query(self):
        response = self.client.post(
            "/api/ai/site-recommend",
            json={"query": "<script>alert(1)</script> Python 调试", "limit": 100},
            headers=self.headers(),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertNotIn("<script>", payload["data"]["query"])
        self.assertEqual(len(payload["data"]["items"]), 1)
        item = payload["data"]["items"][0]
        self.assertEqual(item["id"], 1)
        self.assertEqual(item["url"], "https://python-debug.example")
        self.assertTrue(item["reason"])
        self.assertIn("match_score", item)

    def test_route_returns_empty_items_for_no_match(self):
        response = self.client.post(
            "/api/ai/site-recommend",
            json={"query": "量子烹饪机器人"},
            headers=self.headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["items"], [])

    def test_route_includes_relevant_sites_beyond_the_first_160_candidates(self):
        self.database.candidates = [
            site(index, f"通用工具 {index}", f"https://general-{index}.example")
            for index in range(1, 161)
        ] + [
            site(161, "DeepL 翻译", "https://www.deepl.com/translator"),
            site(162, "百度翻译", "https://fanyi.baidu.com/"),
        ]

        response = self.client.post(
            "/api/ai/site-recommend",
            json={"query": "翻译"},
            headers=self.headers(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item["id"] for item in response.get_json()["data"]["items"]},
            {161, 162},
        )
        self.assertEqual(self.database.site_query_limits[-1], 1000)


if __name__ == "__main__":
    unittest.main()
