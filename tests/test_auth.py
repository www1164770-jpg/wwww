import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.setex_calls = []

    def setex(self, key, ttl, value):
        self.setex_calls.append((key, ttl, value))
        self.values[key] = value
        return True

    def getdel(self, key):
        return self.values.pop(key, None)

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        self.values.pop(key, None)
        return True


class FakeCursor:
    def __init__(self, fetchone_value=None, fetchall_value=None):
        self.fetchone_value = fetchone_value
        self.fetchall_value = fetchall_value or []
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.fetchone_value

    def fetchall(self):
        return self.fetchall_value


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_instance = cursor
        self.committed = False
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        self.closed = True


class AuthExchangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app_module = app_module
        cls.client = app_module.app.test_client()

    def test_exchange_code_uses_secure_random_and_60_second_ttl(self):
        redis_client = FakeRedis()
        with patch.object(self.app_module, "redis_client", redis_client), patch.object(
            self.app_module.secrets, "token_urlsafe", return_value="secure-code"
        ):
            code = self.app_module.issue_authing_exchange_code(7, "/favorites")

        self.assertEqual(code, "secure-code")
        self.assertEqual(len(redis_client.setex_calls), 1)
        key, ttl, raw_value = redis_client.setex_calls[0]
        self.assertEqual(ttl, 60)
        self.assertEqual(key, "authing_exchange:secure-code")
        self.assertEqual(json.loads(raw_value), {"user_id": 7, "redirect": "/favorites"})

    def test_exchange_code_is_consumed_only_once(self):
        redis_client = FakeRedis()
        redis_client.values["authing_exchange:one-time"] = json.dumps(
            {"user_id": 7, "redirect": "/"}
        )
        with patch.object(self.app_module, "redis_client", redis_client):
            first = self.app_module.consume_authing_exchange_code("one-time")
            second = self.app_module.consume_authing_exchange_code("one-time")

        self.assertEqual(first, {"user_id": 7, "redirect": "/"})
        self.assertIsNone(second)

    def test_exchange_code_uses_atomic_lua_fallback_without_getdel(self):
        class LuaRedis:
            def __init__(self):
                self.value = json.dumps({"user_id": 7, "redirect": "/"})
                self.eval_calls = 0

            def eval(self, _script, _numkeys, _key):
                self.eval_calls += 1
                value, self.value = self.value, None
                return value

        redis_client = LuaRedis()
        with patch.object(self.app_module, "redis_client", redis_client):
            first = self.app_module.consume_authing_exchange_code("lua-code")
            second = self.app_module.consume_authing_exchange_code("lua-code")

        self.assertEqual(first, {"user_id": 7, "redirect": "/"})
        self.assertIsNone(second)
        self.assertEqual(redis_client.eval_calls, 2)

    def test_redirect_must_be_an_internal_relative_path(self):
        normalize = self.app_module.normalize_frontend_redirect

        self.assertEqual(normalize("/favorites"), "/favorites")
        self.assertEqual(normalize("/category/1"), "/category/1")
        for unsafe in ("https://evil.com", "http://evil.com", "//evil.com", r"\evil.com"):
            self.assertEqual(normalize(unsafe), "/")

    def test_unknown_exchange_code_is_rejected(self):
        with patch.object(self.app_module, "redis_client", FakeRedis()):
            response = self.client.post(
                "/api/authing/exchange", json={"code": "missing"}
            )
        self.assertIn(response.status_code, (400, 401))

    def test_redis_failure_returns_service_unavailable(self):
        class BrokenRedis:
            def getdel(self, _key):
                raise RuntimeError("redis down")

        with patch.object(self.app_module, "redis_client", BrokenRedis()):
            response = self.client.post("/api/authing/exchange", json={"code": "x"})

        self.assertEqual(response.status_code, 503)

    def test_exchange_returns_same_auth_session_shape_as_local_login(self):
        redis_client = FakeRedis()
        redis_client.values["authing_exchange:valid"] = json.dumps(
            {"user_id": 7, "redirect": "/profile"}
        )
        user = {
            "id": 7,
            "username": "authing-user",
            "email": "authing@example.com",
            "role": "user",
            "questionnaire_completed": 1,
        }
        with patch.object(self.app_module, "redis_client", redis_client), patch.object(
            self.app_module, "user_by_id", return_value=user
        ), patch.object(
            self.app_module, "create_project_token", return_value="access-token"
        ), patch.object(
            self.app_module, "create_refresh_token", return_value="refresh-token"
        ):
            response = self.client.post(
                "/api/authing/exchange", json={"code": "valid"}
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        self.assertEqual(
            set(
                (
                    "access_token",
                    "refresh_token",
                    "user_info",
                    "user_role",
                    "questionnaire_completed",
                )
            ),
            set(data).intersection(
                {
                    "access_token",
                    "refresh_token",
                    "user_info",
                    "user_role",
                    "questionnaire_completed",
                }
            ),
        )
        self.assertEqual(data["redirect"], "/profile")


class LocalAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app_module = app_module
        cls.client = app_module.app.test_client()

    def test_registration_rejects_missing_required_fields(self):
        for payload in ({}, {"username": "alice"}, {"email": "a@example.com"}):
            with self.subTest(payload=payload), patch.object(
                self.app_module, "redis_client", FakeRedis()
            ):
                response = self.client.post("/api/auth/register", json=payload)
            self.assertEqual(response.status_code, 400)

    def test_registration_rejects_invalid_email_and_short_password(self):
        redis_client = FakeRedis()
        redis_client.values["verify_code:a@example.com"] = "123456"
        with patch.object(self.app_module, "redis_client", redis_client):
            invalid_email = self.client.post(
                "/api/auth/register",
                json={
                    "username": "alice",
                    "email": "not-an-email",
                    "password": "password",
                    "code": "123456",
                },
            )
            short_password = self.client.post(
                "/api/auth/register",
                json={
                    "username": "alice",
                    "email": "a@example.com",
                    "password": "short",
                    "code": "123456",
                },
            )

        self.assertEqual(invalid_email.status_code, 400)
        self.assertEqual(short_password.status_code, 400)

    def test_registration_success_deletes_verification_code_after_commit(self):
        redis_client = FakeRedis()
        redis_client.values["verify_code:alice@example.com"] = "123456"
        connection = FakeConnection(FakeCursor(fetchone_value=None))
        with patch.object(self.app_module, "redis_client", redis_client), patch.object(
            self.app_module, "get_db_connection", return_value=connection
        ), patch.object(
            self.app_module, "generate_password_hash", return_value="hashed"
        ):
            response = self.client.post(
                "/api/auth/register",
                json={
                    "username": " alice ",
                    "email": "Alice@Example.com ",
                    "password": "password1",
                    "code": "123456",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(connection.committed)
        self.assertNotIn("verify_code:alice@example.com", redis_client.values)

    def test_send_code_does_not_store_code_when_email_fails(self):
        redis_client = FakeRedis()
        with patch.object(self.app_module, "redis_client", redis_client), patch.object(
            self.app_module,
            "send_verification_email",
            return_value=(False, "smtp down"),
        ):
            response = self.client.post(
                "/api/auth/send-code", json={"email": "alice@example.com"}
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(redis_client.setex_calls, [])

    def test_login_rejects_missing_account_or_password(self):
        missing_account = self.client.post(
            "/api/auth/login", json={"account": "", "password": "secret"}
        )
        missing_password = self.client.post(
            "/api/auth/login", json={"account": "alice", "password": ""}
        )

        self.assertEqual(missing_account.status_code, 400)
        self.assertEqual(missing_password.status_code, 400)

    def test_wrong_password_returns_401(self):
        cursor = FakeCursor(
            fetchone_value={
                "id": 1,
                "username": "alice",
                "email": "alice@example.com",
                "password_hash": "hash",
                "role": "user",
            }
        )
        connection = FakeConnection(cursor)
        with patch.object(self.app_module, "get_db_connection", return_value=connection), patch.object(
            self.app_module, "check_password_hash", return_value=False
        ):
            response = self.client.post(
                "/api/auth/login", json={"account": "alice", "password": "wrong"}
            )

        self.assertEqual(response.status_code, 401)

    def test_successful_login_returns_common_auth_session_data(self):
        user = {
            "id": 1,
            "username": "alice",
            "email": "alice@example.com",
            "password_hash": "hash",
            "role": "user",
            "questionnaire_completed": 0,
        }
        connection = FakeConnection(FakeCursor(fetchone_value=user))
        with patch.object(self.app_module, "get_db_connection", return_value=connection), patch.object(
            self.app_module, "check_password_hash", return_value=True
        ), patch.object(
            self.app_module, "create_access_token", return_value="access-token"
        ), patch.object(
            self.app_module, "create_refresh_token", return_value="refresh-token"
        ):
            response = self.client.post(
                "/api/auth/login", json={"account": " alice ", "password": "secret"}
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        self.assertEqual(data["access_token"], "access-token")
        self.assertEqual(data["refresh_token"], "refresh-token")
        self.assertEqual(data["user_info"]["username"], "alice")
        self.assertEqual(data["user_role"], "user")
        self.assertFalse(data["questionnaire_completed"])

    def test_current_user_endpoint_requires_jwt(self):
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)

    def test_current_user_endpoint_returns_database_user_data(self):
        user = {
            "id": 1,
            "username": "alice",
            "email": "alice@example.com",
            "role": "admin",
            "questionnaire_completed": 1,
        }
        connection = FakeConnection(FakeCursor(fetchone_value=user))
        with self.app_module.app.app_context():
            access_token = self.app_module.create_access_token(identity="alice")
        with patch.object(self.app_module, "get_db_connection", return_value=connection):
            response = self.client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        self.assertEqual(data["user_info"]["username"], "alice")
        self.assertEqual(data["user_role"], "admin")
        self.assertTrue(data["questionnaire_completed"])

    def test_refresh_accepts_refresh_token_but_rejects_access_token(self):
        with self.app_module.app.app_context():
            access_token = self.app_module.create_access_token(identity="alice")
            refresh_token = self.app_module.create_refresh_token(identity="alice")

        access_response = self.client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        refresh_response = self.client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )

        self.assertEqual(access_response.status_code, 401)
        self.assertEqual(refresh_response.status_code, 200)
        self.assertTrue(refresh_response.get_json().get("access_token"))

    def test_normal_user_cannot_access_admin_route(self):
        user = {"id": 1, "username": "alice", "role": "user"}
        connection = FakeConnection(FakeCursor(fetchone_value=user))
        with self.app_module.app.app_context():
            access_token = self.app_module.create_access_token(identity="alice")
        with patch.object(self.app_module, "get_db_connection", return_value=connection):
            response = self.client.get(
                "/api/admin/dashboard",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        self.assertEqual(response.status_code, 403)


class WebsiteWriteAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app_module = app_module
        cls.client = app_module.app.test_client()

        with app_module.app.app_context():
            cls.access_token = app_module.create_access_token(identity="alice")

    def test_website_write_routes_require_jwt(self):
        requests = (
            ("post", "/api/websites", {"name": "Example", "url": "https://example.com"}),
            ("put", "/api/websites/1", {"name": "Example"}),
            ("delete", "/api/websites/1", None),
        )

        for method, path, payload in requests:
            with self.subTest(method=method, path=path):
                response = getattr(self.client, method)(path, json=payload)
                self.assertEqual(response.status_code, 401)

    def test_normal_user_cannot_write_websites(self):
        connection = FakeConnection(FakeCursor(fetchone_value={"role": "user"}))
        requests = (
            ("post", "/api/websites", {"name": "Example", "url": "https://example.com"}),
            ("put", "/api/websites/1", {"name": "Example"}),
            ("delete", "/api/websites/1", None),
        )

        with patch.object(self.app_module, "get_db_connection", return_value=connection):
            for method, path, payload in requests:
                with self.subTest(method=method, path=path):
                    response = getattr(self.client, method)(
                        path,
                        json=payload,
                        headers={"Authorization": f"Bearer {self.access_token}"},
                    )
                    self.assertEqual(response.status_code, 403)

    def test_admin_can_enter_existing_website_write_logic(self):
        connection = FakeConnection(FakeCursor(fetchone_value={"role": "admin"}))
        site = type("Site", (), {"id": 12})()

        with patch.object(self.app_module, "get_db_connection", return_value=connection), patch.object(
            self.app_module, "Website", return_value=site
        ), patch.object(self.app_module.db.session, "add", return_value=None), patch.object(
            self.app_module.db.session, "commit", return_value=None
        ):
            response = self.client.post(
                "/api/websites",
                json={"name": "Example", "url": "https://example.com"},
                headers={"Authorization": f"Bearer {self.access_token}"},
            )

        self.assertEqual(response.status_code, 201)


class LoggingSanitizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app_extensions as app_extensions_module

        cls.sanitize_log_data = staticmethod(app_extensions_module.sanitize_log_data)

    def test_sanitizes_sensitive_fields_recursively_without_mutating_input(self):
        payload = {
            "username": "test",
            "password": "12345678",
            "nested": {"access_token": "JWT"},
            "items": [{"Verification_Code": "654321"}],
        }

        sanitized = self.sanitize_log_data(payload)

        self.assertEqual(payload["password"], "12345678")
        self.assertEqual(sanitized["username"], "test")
        self.assertEqual(sanitized["password"], "[REDACTED]")
        self.assertEqual(sanitized["nested"]["access_token"], "[REDACTED]")
        self.assertEqual(sanitized["items"][0]["Verification_Code"], "[REDACTED]")


class ProductionSecretTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app_module = app_module

    def test_development_can_use_default_secret(self):
        with patch.dict(os.environ, {"APP_ENV": "development"}, clear=True):
            config = self.app_module.get_secret_config()

        self.assertEqual(config["flask_secret"], "dev-secret-key-change-me")
        self.assertEqual(config["jwt_secret"], "dev-secret-key-change-me")

    def test_production_requires_explicit_distinct_non_default_secrets(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "FLASK_SECRET_KEY": "flask-secret-for-test",
                "JWT_SECRET_KEY": "jwt-secret-for-test",
            },
            clear=True,
        ):
            config = self.app_module.get_secret_config()

        self.assertEqual(config["flask_secret"], "flask-secret-for-test")
        self.assertEqual(config["jwt_secret"], "jwt-secret-for-test")

        invalid_configs = (
            {"APP_ENV": "production", "JWT_SECRET_KEY": "jwt-only"},
            {"APP_ENV": "production", "FLASK_SECRET_KEY": "flask-only"},
            {
                "APP_ENV": "production",
                "FLASK_SECRET_KEY": "same-secret",
                "JWT_SECRET_KEY": "same-secret",
            },
            {
                "APP_ENV": "production",
                "FLASK_SECRET_KEY": "dev-secret-key-change-me",
                "JWT_SECRET_KEY": "jwt-secret",
            },
        )
        for env in invalid_configs:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True):
                with self.assertRaises(RuntimeError):
                    self.app_module.get_secret_config()


if __name__ == "__main__":
    unittest.main()
