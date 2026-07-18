import re
import base64
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pymysql
from werkzeug.security import check_password_hash


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
MIGRATION_PATH = (
    BACKEND_DIR
    / "sql"
    / "migrations"
    / "20260716_add_authing_identity_fields.sql"
)

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


class MemoryUsersCursor:
    def __init__(self, connection):
        self.connection = connection
        self.fetchone_value = None
        self.fetchall_value = []
        self.lastrowid = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        params = list(params or [])
        normalized = " ".join(sql.lower().split())
        self.connection.executed.append((normalized, tuple(params)))
        self.fetchone_value = None
        self.fetchall_value = []
        self.rowcount = 0

        if normalized.startswith("show columns from users"):
            fields = (
                "id",
                "username",
                "email",
                "password_hash",
                "authing_sub",
                "login_provider",
                "avatar_url",
                "role",
                "status",
                "questionnaire_completed",
                "created_at",
            )
            self.fetchall_value = [{"Field": field} for field in fields]
            return

        if normalized.startswith("select * from users where authing_sub=%s or email=%s"):
            sub, email = params
            self.fetchone_value = next(
                (
                    user
                    for user in self.connection.users
                    if user.get("authing_sub") == sub or user.get("email") == email
                ),
                None,
            )
            return

        if normalized.startswith("select * from users where authing_sub=%s"):
            sub = params[0]
            self.fetchone_value = next(
                (
                    user
                    for user in self.connection.users
                    if user.get("authing_sub") == sub
                ),
                None,
            )
            return

        if normalized.startswith("select * from users where email=%s"):
            email = params[0]
            self.fetchone_value = next(
                (user for user in self.connection.users if user.get("email") == email),
                None,
            )
            return

        if normalized.startswith("select id from users where username=%s"):
            username = params[0]
            user = next(
                (
                    user
                    for user in self.connection.users
                    if user.get("username") == username
                ),
                None,
            )
            self.fetchone_value = {"id": user["id"]} if user else None
            return

        if normalized.startswith("select * from users where id=%s"):
            user_id = params[0]
            self.fetchone_value = next(
                (user for user in self.connection.users if user.get("id") == user_id),
                None,
            )
            return

        if normalized.startswith("update users set "):
            assignments = normalized.split(" set ", 1)[1].split(" where ", 1)[0]
            fields = [
                assignment.split("=", 1)[0].strip()
                for assignment in assignments.split(",")
            ]
            guarded_authing_bind = (
                "and (authing_sub is null or authing_sub=%s)" in normalized
            )
            if guarded_authing_bind:
                user_id = params[-2]
                allowed_sub = params[-1]
                update_values = params[:-2]
            else:
                user_id = params[-1]
                allowed_sub = None
                update_values = params[:-1]
            user = next(user for user in self.connection.users if user["id"] == user_id)
            if guarded_authing_bind and self.connection.concurrent_bind_sub_once:
                user["authing_sub"] = self.connection.concurrent_bind_sub_once
                self.connection.concurrent_bind_sub_once = None
            if guarded_authing_bind and user.get("authing_sub") not in (
                None,
                allowed_sub,
            ):
                return
            for field, value in zip(fields, update_values):
                user[field] = value
            self.rowcount = 1
            return

        if normalized.startswith("insert into users"):
            if self.connection.insert_exception is not None:
                raise self.connection.insert_exception

            start = normalized.index("(") + 1
            end = normalized.index(")", start)
            fields = [
                field.strip().strip("`")
                for field in normalized[start:end].split(",")
            ]
            row = dict(zip(fields, params))

            if len(row.get("username", "")) > 50:
                raise pymysql.err.DataError(1406, "username too long")
            if len(row.get("email", "")) > 120:
                raise pymysql.err.DataError(1406, "email too long")

            if self.connection.duplicate_username_once:
                self.connection.duplicate_username_once = False
                self.connection.users.append(
                    {
                        "id": self.connection.next_id,
                        "username": row["username"],
                        "email": f"competitor-{self.connection.next_id}@example.com",
                        "password_hash": "hash",
                        "authing_sub": f"competitor-{self.connection.next_id}",
                        "login_provider": "local",
                        "role": "user",
                    }
                )
                self.connection.next_id += 1
                raise pymysql.err.IntegrityError(1062, "duplicate username")

            for existing in self.connection.users:
                for field in ("username", "email", "authing_sub"):
                    if row.get(field) is not None and existing.get(field) == row.get(field):
                        raise pymysql.err.IntegrityError(1062, f"duplicate {field}")

            row["id"] = self.connection.next_id
            self.connection.next_id += 1
            row.setdefault("role", "user")
            row.setdefault("status", "active")
            row.setdefault("questionnaire_completed", 0)
            self.connection.users.append(row)
            self.lastrowid = row["id"]
            return

        raise AssertionError(f"Unexpected SQL: {normalized}")

    def fetchone(self):
        return self.fetchone_value

    def fetchall(self):
        return self.fetchall_value


class MemoryUsersConnection:
    def __init__(self, users=None):
        self.users = [dict(user) for user in (users or [])]
        self.next_id = max((user["id"] for user in self.users), default=0) + 1
        self.executed = []
        self.commit_calls = 0
        self.rollback_calls = 0
        self.closed = False
        self.insert_exception = None
        self.duplicate_username_once = False
        self.concurrent_bind_sub_once = None

    def cursor(self):
        return MemoryUsersCursor(self)

    def commit(self):
        self.commit_calls += 1

    def rollback(self):
        self.rollback_calls += 1

    def close(self):
        self.closed = True


class AuthingIdentityMigrationTests(unittest.TestCase):
    def test_migration_is_focused_and_checks_columns_and_unique_index(self):
        migration = MIGRATION_PATH.read_text(encoding="utf-8")
        normalized = " ".join(migration.lower().split())

        self.assertIn("information_schema.columns", normalized)
        self.assertIn("information_schema.statistics", normalized)
        self.assertIn("add column `authing_sub` varchar(128) null", normalized)
        self.assertIn(
            "add column `login_provider` varchar(50) default ''local''",
            normalized,
        )
        self.assertIn(
            "add unique index `uq_users_authing_sub` (`authing_sub`)",
            normalized,
        )
        self.assertIn(
            "index_columns.index_name = authing_index.index_name",
            normalized,
        )
        self.assertIn(
            "select count(*) from information_schema.statistics as index_columns",
            normalized,
        )
        self.assertNotIn("avatar_url", normalized)
        self.assertNotIn("drop ", normalized)
        self.assertNotIn("delete ", normalized)
        self.assertNotIn("update ", normalized)

    def test_user_model_declares_authing_identity_fields(self):
        from models import User

        authing_sub = User.__table__.columns["authing_sub"]
        login_provider = User.__table__.columns["login_provider"]

        self.assertEqual(authing_sub.type.length, 128)
        self.assertTrue(authing_sub.nullable)
        self.assertTrue(authing_sub.unique)
        self.assertEqual(login_provider.type.length, 50)
        self.assertEqual(login_provider.default.arg, "local")


class AuthingIdentityHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app_module = app_module

    def test_email_is_trimmed_and_lowercased(self):
        self.assertEqual(
            self.app_module.normalize_authing_user_email(
                "  Alice+GitHub@Example.COM \n"
            ),
            "alice+github@example.com",
        )
        self.assertIsNone(self.app_module.normalize_authing_user_email(None))
        self.assertIsNone(self.app_module.normalize_authing_user_email("   "))

    def test_missing_email_uses_stable_bounded_sub_digest(self):
        first = self.app_module.build_authing_placeholder_email(
            "github|stable/sub/用户"
        )
        repeated = self.app_module.build_authing_placeholder_email(
            "github|stable/sub/用户"
        )
        different = self.app_module.build_authing_placeholder_email(
            "github|different-user"
        )

        self.assertEqual(first, repeated)
        self.assertNotEqual(first, different)
        self.assertLessEqual(len(first), 120)
        self.assertRegex(first, re.compile(r"^authing_[0-9a-f]{64}@authing\.local$"))

    def test_username_removes_controls_and_is_limited_to_fifty_characters(self):
        username = self.app_module.sanitize_authing_username(
            "  Alice\x00\n" + "长" * 80
        )

        self.assertNotIn("\x00", username)
        self.assertNotIn("\n", username)
        self.assertLessEqual(len(username), 50)
        self.assertTrue(username.startswith("Alice"))

    def test_username_candidate_suffixes_stay_within_limit(self):
        base = "x" * 50
        digest = "1234567890abcdef"

        candidates = [
            self.app_module.build_authing_username_candidate(base, digest, attempt)
            for attempt in range(4)
        ]

        self.assertEqual(len(candidates), len(set(candidates)))
        self.assertTrue(all(len(candidate) <= 50 for candidate in candidates))


class AuthingUserSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app_module = app_module

    def sync(self, connection, userinfo):
        with patch.object(
            self.app_module, "get_db_connection", return_value=connection
        ):
            return self.app_module.find_or_create_authing_user(userinfo)

    def test_existing_sub_user_is_reused_without_overwriting_local_fields(self):
        connection = MemoryUsersConnection(
            [
                {
                    "id": 1,
                    "username": "local-admin",
                    "email": "authing_old@authing.local",
                    "password_hash": "local-password-hash",
                    "authing_sub": "github|one",
                    "login_provider": "authing",
                    "avatar_url": "old-avatar",
                    "role": "admin",
                    "questionnaire_completed": 1,
                }
            ]
        )

        user = self.sync(
            connection,
            {
                "sub": "github|one",
                "name": "Remote Name",
                "picture": "new-avatar",
            },
        )

        self.assertEqual(user["id"], 1)
        self.assertEqual(user["username"], "local-admin")
        self.assertEqual(user["password_hash"], "local-password-hash")
        self.assertEqual(user["role"], "admin")
        self.assertEqual(user["questionnaire_completed"], 1)
        self.assertEqual(user["avatar_url"], "new-avatar")

    def test_normalized_email_binds_an_unbound_local_user(self):
        connection = MemoryUsersConnection(
            [
                {
                    "id": 2,
                    "username": "alice",
                    "email": "alice@example.com",
                    "password_hash": "local-hash",
                    "authing_sub": None,
                    "login_provider": "local",
                    "role": "user",
                }
            ]
        )

        user = self.sync(
            connection,
            {
                "sub": "github|alice",
                "email": " Alice@Example.COM ",
                "email_verified": True,
                "picture": "avatar",
            },
        )

        self.assertEqual(user["id"], 2)
        self.assertEqual(user["authing_sub"], "github|alice")
        self.assertEqual(user["login_provider"], "authing")
        self.assertEqual(user["password_hash"], "local-hash")

    def test_missing_email_creates_stable_user_and_reuses_it(self):
        connection = MemoryUsersConnection()
        userinfo = {"sub": "github|no-email", "name": "No Email"}

        first = self.sync(connection, userinfo)
        second = self.sync(connection, userinfo)

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(connection.users), 1)
        self.assertEqual(
            first["email"],
            self.app_module.build_authing_placeholder_email("github|no-email"),
        )

    def test_different_subs_create_different_placeholder_emails(self):
        connection = MemoryUsersConnection()

        first = self.sync(connection, {"sub": "github|one"})
        second = self.sync(connection, {"sub": "github|two"})

        self.assertNotEqual(first["id"], second["id"])
        self.assertNotEqual(first["email"], second["email"])

    def test_username_is_bounded_and_collision_uses_a_unique_suffix(self):
        connection = MemoryUsersConnection(
            [
                {
                    "id": 1,
                    "username": "x" * 50,
                    "email": "existing@example.com",
                    "password_hash": "hash",
                    "authing_sub": "existing-sub",
                }
            ]
        )

        user = self.sync(
            connection,
            {
                "sub": "github|long-name",
                "name": "x" * 80,
                "email": "new@example.com",
                "email_verified": True,
            },
        )

        self.assertLessEqual(len(user["username"]), 50)
        self.assertNotEqual(user["username"], "x" * 50)

    def test_email_with_different_existing_authing_sub_is_rejected(self):
        connection = MemoryUsersConnection(
            [
                {
                    "id": 3,
                    "username": "alice",
                    "email": "alice@example.com",
                    "password_hash": "hash",
                    "authing_sub": "github|old",
                }
            ]
        )

        with self.assertRaises(self.app_module.AuthingIdentityConflict):
            self.sync(
                connection,
                {
                    "sub": "github|new",
                    "email": "alice@example.com",
                    "email_verified": True,
                },
            )

        self.assertEqual(connection.users[0]["authing_sub"], "github|old")
        self.assertGreaterEqual(connection.rollback_calls, 1)

    def test_sub_and_email_resolving_to_different_users_is_rejected(self):
        connection = MemoryUsersConnection(
            [
                {
                    "id": 4,
                    "username": "sub-user",
                    "email": "old@example.com",
                    "password_hash": "hash",
                    "authing_sub": "github|shared",
                },
                {
                    "id": 5,
                    "username": "email-user",
                    "email": "new@example.com",
                    "password_hash": "hash",
                    "authing_sub": None,
                },
            ]
        )

        with self.assertRaises(self.app_module.AuthingIdentityConflict):
            self.sync(
                connection,
                {
                    "sub": "github|shared",
                    "email": "new@example.com",
                    "email_verified": True,
                },
            )

        self.assertIsNone(connection.users[1]["authing_sub"])

    def test_new_authing_password_hash_does_not_accept_empty_password(self):
        connection = MemoryUsersConnection()

        user = self.sync(connection, {"sub": "github|passwordless"})

        self.assertTrue(user["password_hash"])
        self.assertFalse(check_password_hash(user["password_hash"], ""))

    def test_insert_failure_explicitly_rolls_back(self):
        connection = MemoryUsersConnection()
        connection.insert_exception = RuntimeError("insert failed")

        with self.assertRaises(RuntimeError):
            self.sync(connection, {"sub": "github|broken"})

        self.assertGreaterEqual(connection.rollback_calls, 1)
        self.assertTrue(connection.closed)

    def test_concurrent_duplicate_username_is_retried(self):
        connection = MemoryUsersConnection()
        connection.duplicate_username_once = True

        user = self.sync(
            connection,
            {
                "sub": "github|concurrent",
                "email": "concurrent@example.com",
                "email_verified": True,
                "name": "concurrent",
            },
        )

        self.assertEqual(user["authing_sub"], "github|concurrent")
        self.assertGreaterEqual(connection.rollback_calls, 1)
        self.assertNotEqual(user["username"], "concurrent")

    def test_concurrent_email_binding_cannot_overwrite_another_sub(self):
        connection = MemoryUsersConnection(
            [
                {
                    "id": 6,
                    "username": "race-user",
                    "email": "race@example.com",
                    "password_hash": "local-hash",
                    "authing_sub": None,
                    "login_provider": "local",
                }
            ]
        )
        connection.concurrent_bind_sub_once = "github|winner"

        with self.assertRaises(self.app_module.AuthingIdentityConflict):
            self.sync(
                connection,
                {
                    "sub": "github|loser",
                    "email": "race@example.com",
                    "email_verified": True,
                },
            )

        self.assertEqual(connection.users[0]["authing_sub"], "github|winner")
        self.assertGreaterEqual(connection.rollback_calls, 1)

    def test_unverified_email_does_not_bind_an_existing_local_user(self):
        connection = MemoryUsersConnection(
            [
                {
                    "id": 7,
                    "username": "protected-local",
                    "email": "protected@example.com",
                    "password_hash": "local-hash",
                    "authing_sub": None,
                    "login_provider": "local",
                }
            ]
        )

        user = self.sync(
            connection,
            {
                "sub": "github|unverified",
                "email": "protected@example.com",
                "email_verified": False,
            },
        )

        self.assertEqual(len(connection.users), 2)
        self.assertIsNone(connection.users[0]["authing_sub"])
        self.assertEqual(
            user["email"],
            self.app_module.build_authing_placeholder_email("github|unverified"),
        )

    def test_oversized_email_and_avatar_use_safe_fallbacks(self):
        connection = MemoryUsersConnection()

        user = self.sync(
            connection,
            {
                "sub": "github|oversized",
                "email": f"{'x' * 121}@example.com",
                "email_verified": True,
                "picture": "https://example.com/" + "a" * 300,
            },
        )

        self.assertEqual(
            user["email"],
            self.app_module.build_authing_placeholder_email("github|oversized"),
        )
        self.assertIsNone(user["avatar_url"])


class AuthingCallbackSyncOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app_module = app_module
        cls.client = app_module.app.test_client()

    def callback_state(self, nonce="state-nonce"):
        payload = base64.urlsafe_b64encode(
            json.dumps({"nonce": nonce, "redirect": "/"}).encode("utf-8")
        ).decode("utf-8")
        with self.client.session_transaction() as session:
            session["authing_state_nonce"] = nonce
        return payload

    def authing_service(self):
        class FakeAuthingService:
            def exchange_code_for_token(self, _code):
                return {"access_token": "authing-access-token"}

            def get_user_info(self, _access_token):
                return {
                    "sub": "github|callback",
                    "email": "callback@example.com",
                    "email_verified": True,
                }

        return FakeAuthingService()

    def test_sync_failure_logs_safe_error_id_and_does_not_issue_exchange_code(self):
        error = pymysql.err.DataError(1406, "sensitive@example.com is too long")
        error.authing_sync_stage = "create_user"
        state = self.callback_state()

        with patch.object(
            self.app_module, "AuthingService", return_value=self.authing_service()
        ), patch.object(
            self.app_module, "find_or_create_authing_user", side_effect=error
        ), patch.object(
            self.app_module, "issue_authing_exchange_code"
        ) as issue_exchange, patch.object(
            self.app_module.secrets, "token_hex", return_value="error123"
        ), self.assertLogs(self.app_module.app.logger, level="ERROR") as logs:
            response = self.client.get(
                f"/api/authing/callback?code=auth-code&state={state}"
            )

        issue_exchange.assert_not_called()
        self.assertEqual(response.status_code, 302)
        self.assertIn("authing_error=user_sync_failed", response.location)
        self.assertIn("error_id=error123", response.location)
        combined = "\n".join(logs.output)
        self.assertIn("error_id=error123", combined)
        self.assertIn("exception_type=DataError", combined)
        self.assertIn("method=GET", combined)
        self.assertIn("path=/api/authing/callback", combined)
        self.assertIn("stage=create_user", combined)
        self.assertIn("mysql_error_code=1406", combined)
        self.assertNotIn("sensitive@example.com", combined)
        self.assertNotIn("authing-access-token", combined)

    def test_identity_conflict_log_contains_only_local_ids_and_safe_metadata(self):
        state = self.callback_state()
        conflict = self.app_module.AuthingIdentityConflict(4, 5)

        with patch.object(
            self.app_module, "AuthingService", return_value=self.authing_service()
        ), patch.object(
            self.app_module, "find_or_create_authing_user", side_effect=conflict
        ), patch.object(
            self.app_module.secrets, "token_hex", return_value="conflict123"
        ), self.assertLogs(self.app_module.app.logger, level="ERROR") as logs:
            response = self.client.get(
                f"/api/authing/callback?code=auth-code&state={state}"
            )

        combined = "\n".join(logs.output)
        self.assertIn("authing_error=authing_identity_conflict", response.location)
        self.assertIn("error_id=conflict123", response.location)
        self.assertIn("event=Authing identity conflict", combined)
        self.assertIn("local_user_ids=4,5", combined)
        self.assertIn("error_id=conflict123", combined)
        self.assertNotIn("github|callback", combined)
        self.assertNotIn("callback@example.com", combined)

    def test_exchange_code_is_issued_only_after_successful_sync(self):
        state = self.callback_state()
        events = []

        def sync_user(_userinfo):
            events.append("sync")
            return {"id": 9, "username": "authing-user"}

        def issue_exchange(_user_id, _redirect):
            events.append("exchange")
            return "one-time-code"

        with patch.object(
            self.app_module, "AuthingService", return_value=self.authing_service()
        ), patch.object(
            self.app_module, "find_or_create_authing_user", side_effect=sync_user
        ), patch.object(
            self.app_module,
            "issue_authing_exchange_code",
            side_effect=issue_exchange,
        ):
            response = self.client.get(
                f"/api/authing/callback?code=auth-code&state={state}"
            )

        self.assertEqual(events, ["sync", "exchange"])
        self.assertIn("code=one-time-code", response.location)
        self.assertNotIn("jwt", response.location.lower())
        self.assertNotIn("token=", response.location.lower())


if __name__ == "__main__":
    unittest.main()
