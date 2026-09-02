import json
import unittest
from pathlib import Path

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from backend.personalization import register_personalization_routes


class _FavoriteDatabase:
    settings = {
        1: {"favorites": ["ocean", "ocean", "forest"]},
        2: {"favorites": []},
    }
    favorites = []

    @classmethod
    def reset(cls):
        cls.settings = {
            1: {"favorites": ["ocean", "ocean", "forest"]},
            2: {"favorites": []},
        }
        cls.favorites = []


class _Cursor:
    def __init__(self):
        self.row = None
        self.rows = []
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(sql.split())
        self.row = None
        self.rows = []
        if "SELECT id FROM users" in normalized:
            self.row = {"id": int(params[2])}
        elif normalized.startswith("SELECT settings_json FROM user_personalization_settings"):
            user_id = int(params[0])
            self.row = {"settings_json": json.dumps(_FavoriteDatabase.settings.get(user_id, {}))} if user_id in _FavoriteDatabase.settings else None
        elif normalized.startswith("SELECT theme_key FROM user_theme_favorites"):
            user_id = int(params[0])
            self.rows = [
                {"theme_key": key}
                for favorite_user_id, key in _FavoriteDatabase.favorites
                if favorite_user_id == user_id
            ]
        elif normalized.startswith("INSERT IGNORE INTO user_theme_favorites"):
            user_id, key = int(params[0]), str(params[1])
            if (user_id, key) not in _FavoriteDatabase.favorites:
                _FavoriteDatabase.favorites.append((user_id, key))
                self.rowcount = 1
        elif normalized.startswith("DELETE FROM user_theme_favorites"):
            user_id, key = int(params[0]), str(params[1])
            before = len(_FavoriteDatabase.favorites)
            _FavoriteDatabase.favorites = [item for item in _FavoriteDatabase.favorites if item != (user_id, key)]
            self.rowcount = before - len(_FavoriteDatabase.favorites)
        elif normalized.startswith("INSERT INTO user_personalization_settings"):
            user_id, raw = int(params[0]), params[1]
            _FavoriteDatabase.settings[user_id] = json.loads(raw)

    def executemany(self, sql, values):
        for value in values:
            self.execute(sql, value)

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class _Connection:
    def cursor(self):
        return _Cursor()

    def close(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass


class PersonalizationThemeFavoriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(TESTING=True, JWT_SECRET_KEY="test-personalization-secret-with-32-bytes")
        JWTManager(cls.app)
        register_personalization_routes(cls.app, _Connection)
        with cls.app.app_context():
            cls.a_token = create_access_token(identity="1")
            cls.b_token = create_access_token(identity="2")

    def setUp(self):
        _FavoriteDatabase.reset()

    def request_as(self, token, method, path, **kwargs):
        return self.app.test_client().open(
            path,
            method=method,
            headers={"Authorization": f"Bearer {token}"},
            **kwargs,
        )

    def test_legacy_json_favorites_backfill_to_table_once(self):
        response = self.request_as(self.a_token, "GET", "/api/personalization")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["favorites"], ["ocean", "forest"])
        self.assertEqual(_FavoriteDatabase.favorites, [(1, "ocean"), (1, "forest")])

    def test_duplicate_favorite_is_single_table_row_and_unfavorite_removes_it(self):
        self.request_as(self.a_token, "POST", "/api/personalization/theme-favorites/ocean")
        response = self.request_as(self.a_token, "POST", "/api/personalization/theme-favorites/ocean")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(_FavoriteDatabase.favorites.count((1, "ocean")), 1)
        response = self.request_as(self.a_token, "DELETE", "/api/personalization/theme-favorites/ocean")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn((1, "ocean"), _FavoriteDatabase.favorites)

    def test_user_b_cannot_remove_user_a_favorite(self):
        self.request_as(self.a_token, "POST", "/api/personalization/theme-favorites/ocean")
        response = self.request_as(self.b_token, "DELETE", "/api/personalization/theme-favorites/ocean")
        self.assertEqual(response.status_code, 200)
        self.assertIn((1, "ocean"), _FavoriteDatabase.favorites)

    def test_table_favorites_load_without_a_legacy_settings_document(self):
        _FavoriteDatabase.settings.pop(2)
        self.request_as(self.b_token, "POST", "/api/personalization/theme-favorites/ocean")
        response = self.request_as(self.b_token, "GET", "/api/personalization")
        self.assertEqual(response.get_json()["data"]["favorites"], ["ocean"])

    def test_migration_declares_unique_table_backfill(self):
        migration = (Path(__file__).resolve().parents[1] / "backend/sql/migrations/20260815_add_user_theme_favorites.sql").read_text(encoding="utf-8")
        self.assertIn("UNIQUE KEY uq_user_theme_favorites_user_theme (user_id, theme_key)", migration)
        self.assertIn("INSERT IGNORE INTO user_theme_favorites", migration)
        self.assertIn("JSON_TABLE", migration)


if __name__ == "__main__":
    unittest.main()
