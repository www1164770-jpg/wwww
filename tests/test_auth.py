import os
import sys
import unittest
from datetime import datetime, timedelta
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


class ScriptedCursor(FakeCursor):
    def __init__(self, fetchone_values):
        super().__init__()
        self.fetchone_values = list(fetchone_values)

    def fetchone(self):
        if self.fetchone_values:
            return self.fetchone_values.pop(0)
        return None


class FakeConnection:
    def __init__(self, cursor):
        self.cursor_instance = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


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
        with patch.object(self.app_module, "redis_client", FakeRedis()):
            invalid_email = self.client.post(
                "/api/auth/register",
                json={
                    "username": "alice",
                    "email": "not-an-email",
                    "password": "password",
                },
            )
            short_password = self.client.post(
                "/api/auth/register",
                json={
                    "username": "alice",
                    "email": "a@example.com",
                    "password": "short",
                },
            )

        self.assertEqual(invalid_email.status_code, 400)
        self.assertEqual(short_password.status_code, 400)

    def test_registration_success_uses_local_account_fields_only(self):
        connection = FakeConnection(FakeCursor(fetchone_value=None))
        with patch.object(self.app_module, "get_db_connection", return_value=connection
        ), patch.object(
            self.app_module, "generate_password_hash", return_value="hashed"
        ), patch.object(
            self.app_module, "ensure_registration_code_table", return_value=None
        ), patch.object(
            self.app_module, "_verify_registration_code", return_value=(True, None, None)
        ):
            response = self.client.post(
                "/api/auth/register",
                json={
                    "username": " alice ",
                    "email": "Alice@Example.com ",
                    "password": "password1",
                    "verification_code": "123456",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["code"], "REGISTER_SUCCESS")
        self.assertTrue(connection.committed)

    def test_registration_requires_verification_code(self):
        response = self.client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "a@example.com", "password": "password1"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "CODE_REQUIRED")


class RegistrationVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app_module = app_module
        cls.client = app_module.app.test_client()

    def _valid_record(self, email="a@example.com", code="123456"):
        return {
            "id": 1,
            "code_hash": self.app_module._registration_code_digest(email, code),
            "expires_at": datetime.utcnow() + timedelta(minutes=5),
            "attempt_count": 0,
            "used_at": None,
        }

    def test_send_register_code_rejects_invalid_email_without_smtp(self):
        response = self.client.post(
            "/api/auth/send-register-code", json={"email": "not-an-email"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "EMAIL_INVALID")

    def test_send_register_code_saves_only_after_successful_smtp(self):
        cursor = ScriptedCursor([None, None, {"total": 0}, {"total": 0}])
        connection = FakeConnection(cursor)
        with patch.object(self.app_module, "get_db_connection", return_value=connection), patch.object(
            self.app_module, "ensure_registration_code_table", return_value=None
        ), patch.object(
            self.app_module, "validate_mail_config", return_value=[]
        ), patch.object(
            self.app_module, "send_verification_email", return_value=(True, "OK")
        ) as send_mail:
            response = self.client.post(
                "/api/auth/send-register-code", json={"email": "a@example.com"}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["code"], 0)
        send_mail.assert_called_once()
        self.assertTrue(connection.committed)
        self.assertTrue(any("INSERT INTO email_verification_codes" in sql for sql, _ in cursor.executed))

    def test_send_register_code_reports_missing_mail_configuration(self):
        with patch.object(
            self.app_module, "validate_mail_config", return_value=["MAIL_USERNAME"]
        ), patch.object(self.app_module, "get_db_connection") as get_connection:
            response = self.client.post(
                "/api/auth/send-register-code", json={"email": "a@example.com"}
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "MAIL_CONFIG_MISSING")
        get_connection.assert_not_called()

    def test_send_register_code_does_not_store_code_when_smtp_fails(self):
        cursor = ScriptedCursor([None, None, {"total": 0}, {"total": 0}])
        connection = FakeConnection(cursor)
        with patch.object(self.app_module, "get_db_connection", return_value=connection), patch.object(
            self.app_module, "ensure_registration_code_table", return_value=None
        ), patch.object(
            self.app_module, "validate_mail_config", return_value=[]
        ), patch.object(
            self.app_module, "send_verification_email", return_value=(False, "SMTP_AUTH_FAILED")
        ):
            response = self.client.post(
                "/api/auth/send-register-code", json={"email": "a@example.com"}
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "SMTP_AUTH_FAILED")
        self.assertFalse(any("INSERT INTO email_verification_codes" in sql for sql, _ in cursor.executed))

    def test_wrong_code_is_rejected_and_counted(self):
        cursor = ScriptedCursor([self._valid_record()])
        connection = FakeConnection(cursor)
        with patch.object(self.app_module, "get_db_connection", return_value=connection), patch.object(
            self.app_module, "ensure_registration_code_table", return_value=None
        ):
            response = self.client.post(
                "/api/auth/register",
                json={
                    "username": "alice",
                    "email": "a@example.com",
                    "password": "password1",
                    "verification_code": "654321",
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "CODE_INVALID")
        self.assertTrue(connection.committed)

    def test_correct_code_creates_user_and_marks_code_used(self):
        cursor = ScriptedCursor([self._valid_record(), None, None])
        connection = FakeConnection(cursor)
        with patch.object(self.app_module, "get_db_connection", return_value=connection), patch.object(
            self.app_module, "ensure_registration_code_table", return_value=None
        ), patch.object(
            self.app_module, "generate_password_hash", return_value="hashed"
        ):
            response = self.client.post(
                "/api/auth/register",
                json={
                    "username": "alice",
                    "email": "a@example.com",
                    "password": "password1",
                    "verification_code": "123456",
                },
            )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(connection.committed)
        self.assertTrue(any("used_at" in sql for sql, _ in cursor.executed))

    def test_missing_code_record_has_specific_error(self):
        cursor = ScriptedCursor([None])
        connection = FakeConnection(cursor)
        with patch.object(self.app_module, "get_db_connection", return_value=connection), patch.object(
            self.app_module, "ensure_registration_code_table", return_value=None
        ):
            response = self.client.post(
                "/api/auth/register",
                json={"username": "alice", "email": "a@example.com", "password": "password1", "verification_code": "123456"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "CODE_NOT_FOUND")

    def test_expired_and_used_codes_have_specific_errors(self):
        expired = self._valid_record()
        expired["expires_at"] = datetime.utcnow() - timedelta(seconds=1)
        used = self._valid_record()
        used["used_at"] = datetime.utcnow()
        for record, expected in ((expired, "CODE_EXPIRED"), (used, "CODE_ALREADY_USED")):
            connection = FakeConnection(ScriptedCursor([record]))
            with self.subTest(expected=expected), patch.object(
                self.app_module, "get_db_connection", return_value=connection
            ), patch.object(self.app_module, "ensure_registration_code_table", return_value=None):
                response = self.client.post(
                    "/api/auth/register",
                    json={"username": "alice", "email": "a@example.com", "password": "password1", "verification_code": "123456"},
                )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.get_json()["code"], expected)

    def test_invalid_username_has_specific_error(self):
        response = self.client.post(
            "/api/auth/register",
            json={"username": "a!", "email": "a@example.com", "password": "password1", "verification_code": "123456"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "USERNAME_INVALID")

    def test_database_failure_rolls_back_without_marking_code_used(self):
        cursor = ScriptedCursor([self._valid_record(), None, None])
        connection = FakeConnection(cursor)
        original_execute = cursor.execute

        def fail_user_insert(sql, params=None):
            if "INSERT INTO users" in sql:
                raise RuntimeError("simulated database failure")
            return original_execute(sql, params)

        cursor.execute = fail_user_insert
        with patch.object(self.app_module, "get_db_connection", return_value=connection), patch.object(
            self.app_module, "ensure_registration_code_table", return_value=None
        ):
            response = self.client.post(
                "/api/auth/register",
                json={"username": "alice", "email": "a@example.com", "password": "password1", "verification_code": "123456"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["code"], "DATABASE_ERROR")
        self.assertTrue(connection.rolled_back)
        self.assertFalse(any("UPDATE email_verification_codes SET used_at" in sql for sql, _ in cursor.executed))

    def test_duplicate_username_returns_conflict(self):
        cursor = ScriptedCursor([self._valid_record(), {"id": 9}])
        connection = FakeConnection(cursor)
        with patch.object(self.app_module, "get_db_connection", return_value=connection), patch.object(
            self.app_module, "ensure_registration_code_table", return_value=None
        ):
            response = self.client.post(
                "/api/auth/register",
                json={
                    "username": "alice",
                    "email": "a@example.com",
                    "password": "password1",
                    "verification_code": "123456",
                },
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["code"], "USERNAME_EXISTS")

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
