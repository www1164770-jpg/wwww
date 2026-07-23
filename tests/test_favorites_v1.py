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
        self.sites = {76: {"id": 76, "favorite_count": 0}}
        self.website_columns = {"id", "favorite_count"}
        self.favorites = []

    def connect(self):
        return FakeFavoritesConnection(self)


class FakeFavoritesConnection:
    def __init__(self, database):
        self.database = database

    def cursor(self):
        return FakeFavoritesCursor(self.database)

    def commit(self):
        return None

    def close(self):
        return None


class FakeFavoritesCursor:
    def __init__(self, database):
        self.database = database
        self.result = []
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql, params=None):
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

        if normalized.startswith("select id from favorites where user_id=%s and site_id=%s"):
            user_id, site_id = map(int, params[:2])
            self.result = [
                {"id": index + 1}
                for index, favorite in enumerate(self.database.favorites)
                if favorite["user_id"] == user_id and favorite["site_id"] == site_id
            ]
            return

        if normalized.startswith("insert into favorites") or normalized.startswith("insert ignore into favorites"):
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

        if "from favorites f" in normalized:
            self.result = []
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
        self.assertEqual(body["code"], 401)
        self.assertEqual(body["message"], "登录状态已失效，请重新登录")

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

    def test_remove_favorite_removes_the_record(self):
        self.add_favorite("testuser")
        response = self.client.delete("/api/sites/76/favorite", headers=self.auth_headers("testuser"))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()["data"]["favorited"])
        self.assertEqual(self.database.favorites, [])

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

    def test_missing_authorization_is_rejected(self):
        response = self.client.post("/api/sites/76/favorite", json={"note": "useful"})

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
