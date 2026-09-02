import unittest

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from backend.personalization import register_personalization_routes


class _Cursor:
    def __init__(self):
        self.row = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=()):
        if "SELECT id FROM users" in sql:
            self.row = {"id": int(params[2])}
        elif "FROM user_backgrounds" in sql:
            # This represents a background owned by another user: the query
            # includes user_id and therefore returns no row to user B.
            self.row = None
        elif "UPDATE user_backgrounds SET privacy" in sql:
            self.rowcount = 0

    def fetchone(self):
        return self.row


class _Connection:
    def cursor(self):
        return _Cursor()

    def close(self):
        pass

    def rollback(self):
        pass


class PersonalizationBackgroundAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(TESTING=True, JWT_SECRET_KEY="test-personalization-secret-with-32-bytes")
        JWTManager(cls.app)
        register_personalization_routes(cls.app, _Connection)
        with cls.app.app_context():
            cls.user_b_token = create_access_token(identity="2")

    def request_as_b(self, method, path, **kwargs):
        return self.app.test_client().open(
            path,
            method=method,
            headers={"Authorization": f"Bearer {self.user_b_token}"},
            **kwargs,
        )

    def test_missing_token_is_unauthorized(self):
        response = self.app.test_client().get("/api/personalization/backgrounds/1/file")
        self.assertEqual(response.status_code, 401)

    def test_user_b_cannot_read_user_a_file_or_thumbnail(self):
        self.assertEqual(self.request_as_b("GET", "/api/personalization/backgrounds/1/file").status_code, 404)
        self.assertEqual(self.request_as_b("GET", "/api/personalization/backgrounds/1/thumbnail").status_code, 404)

    def test_user_b_cannot_change_user_a_privacy(self):
        response = self.request_as_b("PATCH", "/api/personalization/backgrounds/1/privacy", json={"privacy": "public"})
        self.assertEqual(response.status_code, 404)
