import unittest
from copy import deepcopy
from pathlib import Path
import sys

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from v1_routes import register_v1_routes


class FakeFavoritesDatabase:
    def __init__(self):
        self.users = [
            {"id": 7, "username": "testuser", "email": "test@example.com", "deleted_at": None},
            {"id": 42, "username": "123456", "email": "numeric@example.com", "deleted_at": None},
            {"id": 123456, "username": "legacy-id", "email": "legacy@example.com", "deleted_at": None},
            {"id": 8, "username": "removed", "email": "removed@example.com", "deleted_at": "2026-01-01"},
        ]
        self.sites = {
            76: {
                "id": 76,
                "name": "Test Site",
                "url": "https://test.example",
                "logo_url": "https://test.example/logo.png",
                "category_id": 3,
                "favorite_count": 0,
            }
        }
        self.website_columns = {"id", "favorite_count"}
        self.favorites = []
        self.raise_favorites_list_error = False
        self.raise_connect_error = False
        self.raise_insert_error = False
        self.raise_delete_error = False
        self.raise_commit_error_once = False
        self.rollback_count = 0
        self.last_sql = ""
        self.favorite_query_sql = ""

    def connect(self):
        if self.raise_connect_error:
            raise RuntimeError("database unavailable")
        return FakeFavoritesConnection(self)


class FakeFavoritesConnection:
    def __init__(self, database):
        self.database = database
        self.favorites_snapshot = deepcopy(database.favorites)
        self.sites_snapshot = deepcopy(database.sites)

    def cursor(self):
        return FakeFavoritesCursor(self.database)

    def commit(self):
        if self.database.raise_commit_error_once:
            self.database.raise_commit_error_once = False
            raise RuntimeError("commit failed")
        return None

    def rollback(self):
        self.database.rollback_count += 1
        self.database.favorites = deepcopy(self.favorites_snapshot)
        self.database.sites = deepcopy(self.sites_snapshot)

    def close(self):
        return None


class FakeFavoritesCursor:
    def __init__(self, database):
        self.database = database
        self.result = []
        self.rowcount = 0
        self.last_sql = ""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql, params=None):
        self.last_sql = sql
        self.database.last_sql = sql
        normalized = " ".join(sql.split()).lower()
        params = tuple(params or ())
        self.result = []
        self.rowcount = 0

        if normalized == "show columns from websites":
            self.result = [{"Field": column} for column in self.database.website_columns]
            return

        if (
            "from users where username=%s or email=%s" in normalized
            or "from users where (username=%s or email=%s)" in normalized
        ):
            identity = str(params[0])
            self.result = [
                deepcopy(user)
                for user in self.database.users
                if user["username"] == identity or user["email"] == identity
            ]
            if "deleted_at is null" in normalized:
                self.result = [user for user in self.result if user["deleted_at"] is None]
            return

        if "from users where id=%s" in normalized:
            user_id = int(params[0])
            self.result = [deepcopy(user) for user in self.database.users if user["id"] == user_id]
            if "deleted_at is null" in normalized:
                self.result = [user for user in self.result if user["deleted_at"] is None]
            return

        if normalized.startswith("select id from websites where id=%s"):
            site = self.database.sites.get(int(params[0]))
            self.result = [{"id": site["id"]}] if site else []
            return

        if normalized.startswith("select id, url from websites"):
            requested_urls = {str(value).rstrip("/").lower() for value in params}
            self.result = [
                {"id": site["id"], "url": site["url"]}
                for site in self.database.sites.values()
                if str(site["url"]).rstrip("/").lower() in requested_urls
            ]
            return

        if normalized.startswith("select id from favorites where user_id=%s and site_id=%s"):
            user_id, site_id = map(int, params[:2])
            self.result = [
                {"id": index + 1}
                for index, favorite in enumerate(self.database.favorites)
                if favorite["user_id"] == user_id and favorite["site_id"] == site_id
            ]
            return

        if normalized.startswith("insert into favorites") or normalized.startswith("insert ignore into favorites"):
            if self.database.raise_insert_error:
                raise RuntimeError("favorite insert failed")
            user_id, site_id, note = params[:3]
            self.database.favorites.append({"user_id": int(user_id), "site_id": int(site_id), "note": note})
            self.rowcount = 1
            return

        if normalized.startswith("update websites set favorite_count"):
            if "favorite_count" not in self.database.website_columns:
                raise RuntimeError("Unknown column 'favorite_count' in 'field list'")
            site = self.database.sites.get(int(params[0]))
            if site:
                if "+1" in normalized:
                    site["favorite_count"] += 1
                else:
                    site["favorite_count"] = max(site["favorite_count"] - 1, 0)
                self.rowcount = 1
            return

        if normalized.startswith("delete from favorites where user_id=%s and site_id=%s"):
            if self.database.raise_delete_error:
                raise RuntimeError("favorite delete failed")
            user_id, site_id = map(int, params[:2])
            before = len(self.database.favorites)
            self.database.favorites = [
                favorite for favorite in self.database.favorites
                if not (favorite["user_id"] == user_id and favorite["site_id"] == site_id)
            ]
            self.rowcount = before - len(self.database.favorites)
            return

        if normalized.startswith("update favorites set note=%s where user_id=%s and site_id=%s"):
            note, user_id, site_id = params[:3]
            for favorite in self.database.favorites:
                if favorite["user_id"] == int(user_id) and favorite["site_id"] == int(site_id):
                    favorite["note"] = note
                    self.rowcount = 1
            return

        if "from favorites f join websites w" in normalized:
            self.database.favorite_query_sql = sql
            if self.database.raise_favorites_list_error:
                raise RuntimeError("favorites query failed")
            user_id = int(params[0])
            self.result = [
                {
                    **deepcopy(self.database.sites[favorite["site_id"]]),
                    "category_name": "Test Category",
                    "favorite_id": index + 1,
                    "note": favorite["note"],
                }
                for index, favorite in enumerate(self.database.favorites)
                if favorite["user_id"] == user_id
            ]
            return

        if "insert into user_behaviors" in normalized:
            return

        raise AssertionError(f"Unexpected SQL: {sql}")

    def fetchone(self):
        return deepcopy(self.result[0]) if self.result else None

    def fetchall(self):
        return deepcopy(self.result)


class FavoritesV1Tests(unittest.TestCase):
    def setUp(self):
        self.database = FakeFavoritesDatabase()
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            JWT_SECRET_KEY="favorites-v1-test-secret-key-long-enough",
        )
        JWTManager(self.app)
        register_v1_routes(self.app, self.database.connect)
        self.client = self.app.test_client()

    def auth_headers(self, identity):
        with self.app.app_context():
            token = create_access_token(identity=identity)
        return {"Authorization": f"Bearer {token}"}

    def assert_login_expired(self, response):
        self.assertEqual(response.status_code, 401)
        body = response.get_json()
        self.assertIn(body["code"], ("AUTH_REQUIRED", 401))
        self.assertIn(body["message"], ("请先登录后操作收藏", "登录状态已失效，请重新登录"))

    def add_favorite(self, identity, site_id=76):
        return self.client.post(
            f"/api/sites/{site_id}/favorite",
            headers=self.auth_headers(identity),
            json={"note": "useful"},
        )

    def test_username_identity_adds_favorite(self):
        response = self.add_favorite("testuser")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["data"]["created"])
        self.assertEqual(self.database.favorites, [{"user_id": 7, "site_id": 76, "note": "useful"}])

    def test_email_identity_adds_favorite(self):
        response = self.add_favorite("test@example.com")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["data"]["created"])
        self.assertEqual(self.database.favorites[0]["user_id"], 7)

    def test_legacy_numeric_identity_adds_favorite(self):
        response = self.add_favorite("7")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.database.favorites[0]["user_id"], 7)

    def test_numeric_username_wins_before_legacy_id_lookup(self):
        response = self.add_favorite("123456")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.database.favorites[0]["user_id"], 42)

    def test_unknown_or_deleted_identity_is_a_safe_401(self):
        self.assert_login_expired(self.add_favorite("missing-user"))
        self.assert_login_expired(self.add_favorite("removed"))
        self.assertEqual(self.database.favorites, [])

    def test_nonexistent_site_is_404_without_creating_favorite(self):
        response = self.add_favorite("testuser", site_id=9999)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.database.favorites, [])

    def test_duplicate_add_is_deduplicated_in_code(self):
        first = self.add_favorite("testuser")
        second = self.add_favorite("testuser")

        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.get_json()["data"]["created"])
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.get_json()["data"]["created"])
        self.assertEqual(len(self.database.favorites), 1)

    def test_add_response_keeps_favorite_id_separate_from_site_id(self):
        response = self.add_favorite("testuser")

        favorite = response.get_json()["data"]["favorite"]
        self.assertEqual(favorite["favoriteId"], 1)
        self.assertEqual(favorite["siteId"], 76)
        self.assertNotEqual(favorite["favoriteId"], favorite["siteId"])

    def test_remove_favorite_removes_the_record(self):
        self.add_favorite("testuser")
        response = self.client.delete("/api/sites/76/favorite", headers=self.auth_headers("testuser"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["data"]["favorited"])
        self.assertEqual(self.database.favorites, [])

    def test_duplicate_remove_is_idempotent_success(self):
        self.add_favorite("testuser")
        first = self.client.delete("/api/sites/76/favorite", headers=self.auth_headers("testuser"))
        second = self.client.delete("/api/sites/76/favorite", headers=self.auth_headers("testuser"))

        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.get_json()["data"]["removed"])
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.get_json()["data"]["removed"])
        self.assertTrue(second.get_json()["data"]["alreadyRemoved"])

    def test_reference_endpoint_rejects_missing_site_data(self):
        response = self.client.post(
            "/api/favorites",
            headers=self.auth_headers("testuser"),
            json={},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["code"], "INVALID_SITE")

    def test_reference_endpoint_returns_site_not_found_for_unknown_url(self):
        response = self.client.post(
            "/api/favorites",
            headers=self.auth_headers("testuser"),
            json={"url": "https://missing.example"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["code"], "SITE_NOT_FOUND")

    def test_reference_endpoint_rejects_malformed_url(self):
        response = self.client.post(
            "/api/favorites",
            headers=self.auth_headers("testuser"),
            json={"url": "https://bad:not-a-port"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["code"], "INVALID_SITE")

    def test_reference_endpoint_accepts_normalized_url(self):
        response = self.client.post(
            "/api/favorites",
            headers=self.auth_headers("testuser"),
            json={"url": "https://test.example/", "note": "url favorite"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["favorite"]["siteId"], 76)

    def test_user_cannot_remove_another_users_favorite(self):
        self.database.favorites = [{"user_id": 42, "site_id": 76, "note": "private"}]

        response = self.client.delete(
            "/api/sites/76/favorite",
            headers=self.auth_headers("testuser"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["data"]["removed"])
        self.assertEqual(self.database.favorites[0]["user_id"], 42)

    def test_insert_error_rolls_back_and_next_request_can_succeed(self):
        self.database.raise_insert_error = True
        failed = self.add_favorite("testuser")

        self.assertEqual(failed.status_code, 503)
        self.assertEqual(failed.get_json()["code"], "FAVORITE_DATABASE_ERROR")
        self.assertGreaterEqual(self.database.rollback_count, 1)
        self.assertEqual(self.database.favorites, [])

        self.database.raise_insert_error = False
        recovered = self.add_favorite("testuser")
        self.assertEqual(recovered.status_code, 200)

    def test_commit_error_rolls_back_relation_and_counter(self):
        self.database.raise_commit_error_once = True

        response = self.add_favorite("testuser")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.database.favorites, [])
        self.assertEqual(self.database.sites[76]["favorite_count"], 0)
        self.assertGreaterEqual(self.database.rollback_count, 1)

    def test_delete_error_rolls_back_and_keeps_existing_favorite(self):
        self.add_favorite("testuser")
        self.database.raise_delete_error = True

        response = self.client.delete(
            "/api/sites/76/favorite",
            headers=self.auth_headers("testuser"),
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "FAVORITE_DATABASE_ERROR")
        self.assertEqual(len(self.database.favorites), 1)

    def test_missing_favorite_count_column_keeps_favorite_relation_working(self):
        self.database.website_columns.remove("favorite_count")
        self.database.sites[76].pop("favorite_count")
        self.app.config["PROPAGATE_EXCEPTIONS"] = False

        add_response = self.add_favorite("testuser")
        remove_response = self.client.delete("/api/sites/76/favorite", headers=self.auth_headers("testuser"))

        self.assertEqual(add_response.status_code, 200)
        self.assertTrue(add_response.get_json()["data"]["created"])
        self.assertEqual(remove_response.status_code, 200)
        self.assertFalse(remove_response.get_json()["data"]["favorited"])
        self.assertEqual(self.database.favorites, [])

    def test_list_and_note_update_reject_unmapped_identity(self):
        list_response = self.client.get("/api/favorites", headers=self.auth_headers("missing-user"))
        update_response = self.client.put(
            "/api/sites/76/favorite",
            headers=self.auth_headers("missing-user"),
            json={"note": "changed"},
        )

        self.assert_login_expired(list_response)
        self.assert_login_expired(update_response)

    def test_real_application_has_one_get_favorites_route_owned_by_v1(self):
        from app import app as real_app

        rules = [
            rule
            for rule in real_app.url_map.iter_rules()
            if rule.rule == "/api/favorites" and "GET" in rule.methods
        ]

        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].endpoint, "v1_favorites")

    def test_added_favorite_is_returned_as_a_complete_site_object(self):
        self.add_favorite("testuser")

        response = self.client.get("/api/favorites", headers=self.auth_headers("testuser"))

        self.assertEqual(response.status_code, 200)
        items = response.get_json()["data"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], 76)
        for field in ("name", "url", "logo_url", "category_id", "category_name", "note"):
            self.assertIn(field, items[0])
        self.assertTrue(items[0]["is_favorited"])
        self.assertEqual(items[0]["siteId"], 76)
        self.assertEqual(items[0]["favoriteId"], 1)
        self.assertEqual(items[0]["categoryName"], "Test Category")

    def test_favorite_list_uses_explicit_fields_and_user_order_index_shape(self):
        self.add_favorite("testuser")

        self.client.get("/api/favorites", headers=self.auth_headers("testuser"))

        query = " ".join(self.database.favorite_query_sql.split()).lower()
        self.assertIn("w.id, w.name, w.url, w.logo_url", query)
        self.assertIn("f.created_at as favorited_at", query)
        self.assertNotIn("select w.*", query)
        self.assertIn("where f.user_id = %s", query)
        self.assertIn("order by f.created_at desc", query)

    def test_favorite_list_supports_numeric_username_and_email_identities(self):
        self.add_favorite("7")
        self.assertEqual(
            self.client.get("/api/favorites", headers=self.auth_headers("7")).get_json()["data"][0]["id"],
            76,
        )

        self.database.favorites = []
        self.add_favorite("test@example.com")
        self.assertEqual(
            self.client.get("/api/favorites", headers=self.auth_headers("test@example.com")).get_json()["data"][0]["id"],
            76,
        )

    def test_favorite_list_returns_safe_500_for_database_errors(self):
        self.database.raise_favorites_list_error = True
        self.app.config["PROPAGATE_EXCEPTIONS"] = False

        response = self.client.get("/api/favorites", headers=self.auth_headers("testuser"))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["code"], 500)
        self.assertFalse(response.get_json()["success"])
        self.assertNotIn("favorites query failed", response.get_json()["message"])

    def test_favorite_list_returns_503_for_database_connection_errors(self):
        self.database.raise_connect_error = True
        self.app.config["PROPAGATE_EXCEPTIONS"] = False

        response = self.client.get("/api/favorites", headers=self.auth_headers("testuser"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "DATABASE_UNAVAILABLE")
        self.assertEqual(response.get_json()["error_code"], "DATABASE_UNAVAILABLE")
        self.assertFalse(response.get_json()["success"])

    def test_missing_authorization_is_rejected(self):
        response = self.client.post("/api/sites/76/favorite", json={"note": "useful"})

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
