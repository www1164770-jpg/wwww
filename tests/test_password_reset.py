import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from werkzeug.security import check_password_hash, generate_password_hash


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app as app_module
import password_reset


class MemoryDatabase:
    def __init__(self):
        self.users = {
            "alice@example.com": {
                "id": 1,
                "username": "alice",
                "email": "alice@example.com",
                "password_hash": generate_password_hash("OldPassword1"),
                "session_version": 0,
                "role": "user",
                "status": "active",
                "deleted_at": None,
                "questionnaire_completed": 0,
            }
        }
        self.codes = []
        self.next_code_id = 1

    def connection(self):
        return MemoryConnection(self)


class MemoryCursor:
    def __init__(self, database):
        self.database = database
        self.result = None
        self.lastrowid = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split()).lower()
        params = params or ()
        self.result = None

        if normalized.startswith("show columns from users like 'session_version'"):
            self.result = {"Field": "session_version"}
            return

        if normalized.startswith("select id, username from users"):
            user = self.database.users.get(params[0].lower())
            self.result = {"id": user["id"], "username": user["username"]} if user else None
            return

        if normalized.startswith("select created_at from password_reset_codes"):
            matches = [item for item in self.database.codes if item["email"] == params[0]]
            latest = max(matches, key=lambda item: (item["created_at"], item["id"]), default=None)
            self.result = {"created_at": latest["created_at"]} if latest else None
            return

        if normalized.startswith("select count(*) as total from password_reset_codes"):
            email, threshold = params
            total = sum(
                1
                for item in self.database.codes
                if item["email"] == email and item["created_at"] >= threshold
            )
            self.result = {"total": total}
            return

        if normalized.startswith("insert into password_reset_codes"):
            user_id, email, code_hash, expires_at, used_at, request_ip, created_at = params
            item = {
                "id": self.database.next_code_id,
                "user_id": user_id,
                "email": email,
                "code_hash": code_hash,
                "expires_at": expires_at,
                "used_at": used_at,
                "attempt_count": 0,
                "request_ip": request_ip,
                "created_at": created_at,
            }
            self.database.next_code_id += 1
            self.database.codes.append(item)
            self.lastrowid = item["id"]
            return

        if normalized.startswith("select r.id, r.user_id"):
            email = params[0]
            matches = [
                item
                for item in self.database.codes
                if item["email"] == email and item["user_id"] is not None
            ]
            latest = max(matches, key=lambda item: (item["created_at"], item["id"]), default=None)
            if latest:
                user = next(
                    user for user in self.database.users.values() if user["id"] == latest["user_id"]
                )
                self.result = {**latest, "username": user["username"]}
            return

        if normalized.startswith("select * from users"):
            account = str(params[0]).lower()
            self.result = next(
                (
                    dict(user)
                    for user in self.database.users.values()
                    if user["username"].lower() == account or user["email"].lower() == account
                ),
                None,
            )
            return

        if normalized.startswith("select session_version from users"):
            username = params[0]
            user = next(
                (user for user in self.database.users.values() if user["username"] == username),
                None,
            )
            self.result = {"session_version": user["session_version"]} if user else None
            return

        if normalized.startswith("update password_reset_codes set attempt_count"):
            attempts, used_at, record_id = params
            record = next(item for item in self.database.codes if item["id"] == record_id)
            record["attempt_count"] = attempts
            record["used_at"] = used_at
            return

        if normalized.startswith("update password_reset_codes set used_at") and "where id=" in normalized:
            used_at, record_id = params
            record = next(item for item in self.database.codes if item["id"] == record_id)
            record["used_at"] = used_at
            return

        if normalized.startswith("update password_reset_codes set used_at") and "where user_id=" in normalized:
            used_at, user_id = params
            for item in self.database.codes:
                if item["user_id"] == user_id and item["used_at"] is None:
                    item["used_at"] = used_at
            return

        if normalized.startswith("update users set password_hash"):
            password_hash, updated_at, user_id = params
            user = next(user for user in self.database.users.values() if user["id"] == user_id)
            user["password_hash"] = password_hash
            user["session_version"] += 1
            user["updated_at"] = updated_at
            return

        raise AssertionError(f"Unexpected SQL: {normalized}")

    def fetchone(self):
        return self.result


class MemoryConnection:
    def __init__(self, database):
        self.database = database
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return MemoryCursor(self.database)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


class PasswordResetTests(unittest.TestCase):
    def setUp(self):
        self.database = MemoryDatabase()
        self.client = app_module.app.test_client()
        app_module.app.config["TESTING"] = True
        app_module.login_failures.clear()

    def request_context(self, send_result=(True, "OK")):
        return (
            patch.object(password_reset, "get_connection", side_effect=self.database.connection),
            patch.object(password_reset, "validate_mail_config", return_value=[]),
            patch.object(password_reset, "check_mail_connection", return_value=(True, "OK")),
            patch.object(password_reset, "send_password_reset_email", return_value=send_result),
        )

    def send_code(self, email="alice@example.com", send_result=(True, "OK")):
        connection_patch, config_patch, preflight_patch, mail_patch = self.request_context(
            send_result
        )
        with connection_patch, config_patch, preflight_patch, mail_patch as send_mail:
            response = self.client.post(
                "/api/auth/forgot-password/send-code", json={"email": email}
            )
        code = send_mail.call_args.args[1] if send_mail.called else None
        return response, code, send_mail

    def add_code(self, code="123456", **changes):
        now = password_reset.utcnow()
        record = {
            "id": self.database.next_code_id,
            "user_id": 1,
            "email": "alice@example.com",
            "code_hash": password_reset._code_digest(
                app_module.app, "alice@example.com", code
            ),
            "expires_at": now + timedelta(minutes=10),
            "used_at": None,
            "attempt_count": 0,
            "request_ip": "127.0.0.1",
            "created_at": now,
            **changes,
        }
        self.database.next_code_id += 1
        self.database.codes.append(record)
        return record

    def reset(self, code="123456", password="NewPassword1", confirm=None):
        with patch.object(password_reset, "get_connection", side_effect=self.database.connection):
            return self.client.post(
                "/api/auth/forgot-password/reset",
                json={
                    "email": "alice@example.com",
                    "code": code,
                    "new_password": password,
                    "confirm_password": password if confirm is None else confirm,
                },
            )

    def test_routes_are_registered_on_the_existing_auth_namespace(self):
        routes = {rule.rule for rule in app_module.app.url_map.iter_rules()}
        self.assertIn("/api/auth/forgot-password/send-code", routes)
        self.assertIn("/api/auth/forgot-password/reset", routes)

    def test_invalid_email_is_rejected_before_sending(self):
        response, _, send_mail = self.send_code("not-an-email")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "EMAIL_INVALID")
        send_mail.assert_not_called()

    def test_missing_mail_configuration_returns_service_error_without_database_access(self):
        with patch.object(
            password_reset, "validate_mail_config", return_value=["MAIL_USERNAME"]
        ), patch.object(password_reset, "get_connection") as get_connection:
            response = self.client.post(
                "/api/auth/forgot-password/send-code",
                json={"email": "alice@example.com"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "MAIL_CONFIG_MISSING")
        get_connection.assert_not_called()

    def test_smtp_authentication_failure_returns_controlled_service_error(self):
        with patch.object(
            password_reset, "validate_mail_config", return_value=[]
        ), patch.object(
            password_reset,
            "check_mail_connection",
            return_value=(False, "SMTP_AUTH_FAILED"),
        ), patch.object(password_reset, "get_connection") as get_connection:
            response = self.client.post(
                "/api/auth/forgot-password/send-code",
                json={"email": "alice@example.com"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "SMTP_AUTH_FAILED")
        get_connection.assert_not_called()

    def test_missing_reset_table_returns_controlled_error_and_logs_migration(self):
        missing_table = Exception(
            1146, "Table 'nav_site.password_reset_codes' doesn't exist"
        )
        with patch.object(
            password_reset, "validate_mail_config", return_value=[]
        ), patch.object(
            password_reset, "check_mail_connection", return_value=(True, "OK")
        ), patch.object(
            password_reset, "get_connection", side_effect=missing_table
        ), self.assertLogs(app_module.app.logger, level="ERROR") as captured:
            response = self.client.post(
                "/api/auth/forgot-password/send-code",
                json={"email": "alice@example.com"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("PASSWORD_RESET_UNAVAILABLE", response.get_json()["code"])
        self.assertTrue(
            any(
                "apply migration 20260806_add_password_reset_codes" in line
                for line in captured.output
            )
        )

    def test_development_console_mode_exposes_code_only_when_explicitly_enabled(self):
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "development",
                "PASSWORD_RESET_MAIL_MODE": "console",
                "PASSWORD_RESET_DEV_SHOW_CODE": "true",
            },
            clear=False,
        ), patch.object(
            password_reset, "get_connection", side_effect=self.database.connection
        ), patch.object(password_reset, "send_password_reset_email") as send_mail:
            response = self.client.post(
                "/api/auth/forgot-password/send-code",
                json={"email": "alice@example.com"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.get_json().get("test_code", ""), r"^\d{6}$")
        send_mail.assert_not_called()

    def test_production_rejects_console_mode_even_when_code_flag_is_enabled(self):
        with patch.dict(
            "os.environ",
            {
                "APP_ENV": "production",
                "PASSWORD_RESET_MAIL_MODE": "console",
                "PASSWORD_RESET_DEV_SHOW_CODE": "true",
            },
            clear=False,
        ), patch.object(password_reset, "get_connection") as get_connection:
            response = self.client.post(
                "/api/auth/forgot-password/send-code",
                json={"email": "alice@example.com"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "MAIL_MODE_INVALID")
        self.assertNotIn("test_code", response.get_json())
        get_connection.assert_not_called()

    def test_registered_and_unregistered_responses_are_identical(self):
        registered, code, send_mail = self.send_code()
        unregistered, _, unknown_send = self.send_code("nobody@example.com")
        self.assertEqual(registered.status_code, 200)
        self.assertEqual(registered.get_json(), unregistered.get_json())
        self.assertRegex(code, r"^\d{6}$")
        send_mail.assert_called_once()
        unknown_send.assert_not_called()

    def test_code_is_sent_and_only_its_digest_is_stored(self):
        response, code, _ = self.send_code()
        self.assertEqual(response.status_code, 200)
        record = self.database.codes[-1]
        self.assertNotEqual(record["code_hash"], code)
        self.assertEqual(len(record["code_hash"]), 64)

    def test_second_send_within_sixty_seconds_is_limited(self):
        first, _, _ = self.send_code()
        second, _, second_mail = self.send_code()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.get_json()["code"], "RESET_CODE_RATE_LIMITED")
        second_mail.assert_not_called()

    def test_sixth_send_within_one_hour_is_limited(self):
        now = password_reset.utcnow()
        for index in range(5):
            self.database.codes.append(
                {
                    "id": index + 1,
                    "user_id": 1,
                    "email": "alice@example.com",
                    "code_hash": "a" * 64,
                    "expires_at": now,
                    "used_at": now,
                    "attempt_count": 0,
                    "request_ip": "127.0.0.1",
                    "created_at": now - timedelta(minutes=index + 2),
                }
            )
        response, _, send_mail = self.send_code()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.get_json()["code"], "RESET_CODE_HOURLY_LIMIT")
        send_mail.assert_not_called()

    def test_mail_failure_does_not_expose_account_and_invalidates_code(self):
        response, _, _ = self.send_code(send_result=(False, "SMTP_SEND_FAILED"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "SMTP_SEND_FAILED")
        self.assertIsNotNone(self.database.codes[-1]["used_at"])

    def test_expired_code_cannot_be_used(self):
        self.add_code(expires_at=password_reset.utcnow() - timedelta(seconds=1))
        response = self.reset()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "RESET_CODE_EXPIRED")

    def test_wrong_code_is_rejected(self):
        record = self.add_code()
        response = self.reset(code="654321")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "RESET_CODE_INVALID")
        self.assertEqual(record["attempt_count"], 1)

    def test_five_wrong_attempts_invalidate_the_code(self):
        record = self.add_code()
        responses = [self.reset(code="654321") for _ in range(5)]
        self.assertEqual(responses[-1].get_json()["code"], "RESET_CODE_LOCKED")
        self.assertEqual(record["attempt_count"], 5)
        self.assertIsNotNone(record["used_at"])
        self.assertEqual(self.reset().get_json()["code"], "RESET_CODE_USED")

    def test_password_confirmation_must_match(self):
        response = self.reset(password="NewPassword1", confirm="Different2")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "PASSWORD_MISMATCH")

    def test_weak_password_is_rejected(self):
        for weak in ("short1", "onlyletters", "12345678"):
            with self.subTest(weak=weak):
                response = self.reset(password=weak)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["code"], "PASSWORD_WEAK")

    def test_valid_code_resets_password_and_cannot_be_reused(self):
        record = self.add_code()
        response = self.reset()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        self.assertIsNotNone(record["used_at"])
        self.assertTrue(
            check_password_hash(
                self.database.users["alice@example.com"]["password_hash"],
                "NewPassword1",
            )
        )
        self.assertEqual(self.reset().get_json()["code"], "RESET_CODE_USED")

    def test_old_login_fails_new_login_succeeds_and_old_jwt_is_revoked(self):
        with patch.object(app_module, "get_db_connection", side_effect=self.database.connection):
            old_login = self.client.post(
                "/api/auth/login",
                json={"account": "alice@example.com", "password": "OldPassword1"},
            )
        self.assertEqual(old_login.status_code, 200)
        old_token = old_login.get_json()["data"]["access_token"]

        self.add_code()
        self.assertEqual(self.reset().status_code, 200)

        with patch.object(app_module, "get_db_connection", side_effect=self.database.connection):
            old_password = self.client.post(
                "/api/auth/login",
                json={"account": "alice@example.com", "password": "OldPassword1"},
            )
            new_password = self.client.post(
                "/api/auth/login",
                json={"account": "alice@example.com", "password": "NewPassword1"},
            )
            old_session = self.client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {old_token}"}
            )

        self.assertEqual(old_password.status_code, 401)
        self.assertEqual(new_password.status_code, 200)
        self.assertEqual(old_session.status_code, 401)
        self.assertEqual(old_session.get_json()["code"], "AUTH_REVOKED")

    def test_pre_migration_jwt_without_version_claim_is_revoked_after_reset(self):
        with app_module.app.app_context():
            legacy_token = app_module.create_access_token(identity="alice")

        self.add_code()
        self.assertEqual(self.reset().status_code, 200)

        with patch.object(app_module, "get_db_connection", side_effect=self.database.connection):
            response = self.client.get(
                "/api/auth/me", headers={"Authorization": f"Bearer {legacy_token}"}
            )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["code"], "AUTH_REVOKED")


class PasswordResetMigrationTests(unittest.TestCase):
    def test_migration_is_idempotent_and_contains_required_fields_and_indexes(self):
        migration = (
            BACKEND_DIR / "sql" / "migrations" / "20260806_add_password_reset_codes.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS password_reset_codes", migration)
        for field in (
            "id",
            "user_id",
            "email",
            "code_hash",
            "expires_at",
            "used_at",
            "attempt_count",
            "request_ip",
            "created_at",
        ):
            self.assertRegex(migration, rf"\b{field}\b")
        for index in (
            "idx_password_reset_email",
            "idx_password_reset_user_id",
            "idx_password_reset_expires_at",
        ):
            self.assertIn(index, migration)
        self.assertIn("COLUMN_NAME = 'session_version'", migration)
        self.assertIn("ALTER TABLE users ADD COLUMN session_version", migration)


if __name__ == "__main__":
    unittest.main()
