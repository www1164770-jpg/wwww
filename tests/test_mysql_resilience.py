import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pymysql


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import db_pool
import mysql_service


class DatabaseRetryTests(unittest.TestCase):
    def test_transient_checkout_is_retried_with_bounded_delays(self):
        healthy = Mock()
        pool = Mock()
        pool.connection.side_effect = [
            pymysql.err.OperationalError(2003, "unavailable"),
            pymysql.err.OperationalError(2006, "gone away"),
            pymysql.err.OperationalError(2013, "lost connection"),
            healthy,
        ]

        with patch.object(db_pool, "get_pool", return_value=pool), patch.object(
            db_pool.time, "sleep"
        ) as sleep:
            result = db_pool.get_connection()

        self.assertIs(result, healthy)
        healthy.ping.assert_called_once_with(reconnect=True)
        self.assertEqual(pool.connection.call_count, 4)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.5, 1.0])

    def test_authentication_and_unknown_database_errors_are_not_retried(self):
        for code in (1045, 1049):
            with self.subTest(code=code):
                pool = Mock()
                pool.connection.side_effect = pymysql.err.OperationalError(code, "configuration error")
                with patch.object(db_pool, "get_pool", return_value=pool), patch.object(
                    db_pool.time, "sleep"
                ) as sleep:
                    with self.assertRaises(pymysql.err.OperationalError):
                        db_pool.get_connection()
                self.assertEqual(pool.connection.call_count, 1)
                sleep.assert_not_called()


class MySQLServiceTests(unittest.TestCase):
    @staticmethod
    def completed(returncode=0, stdout="", stderr=""):
        return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)

    def test_running_service_is_not_started_again(self):
        running = self.completed(stdout="STATE              : 4  RUNNING")
        with patch.object(mysql_service, "_run_sc", return_value=running) as run_sc:
            mysql_service.ensure_mysql_service(time.monotonic() + 1)
        run_sc.assert_called_once_with("query", "MySQL97")

    def test_access_denied_has_actionable_failure(self):
        stopped = self.completed(stdout="STATE              : 1  STOPPED")
        denied = self.completed(returncode=5, stderr="OpenService FAILED 5: Access is denied")
        with patch.object(mysql_service, "_run_sc", side_effect=[stopped, denied]):
            with self.assertRaises(mysql_service.MySQLServicePermissionError) as raised:
                mysql_service.ensure_mysql_service(time.monotonic() + 1)
        self.assertIn("管理员身份", str(raised.exception))

    def test_select_one_is_required_for_readiness(self):
        cursor = Mock()
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=False)
        connection = Mock()
        connection.cursor.return_value = cursor

        mysql_service.wait_for_database_connection(
            time.monotonic() + 1,
            connection_factory=Mock(return_value=connection),
        )

        cursor.execute.assert_called_once_with("SELECT 1")
        cursor.fetchone.assert_called_once_with()
        connection.close.assert_called_once_with()

    def test_bad_password_fails_without_waiting(self):
        factory = Mock(
            side_effect=pymysql.err.OperationalError(1045, "access denied")
        )
        with patch.object(mysql_service.time, "sleep") as sleep:
            with self.assertRaises(mysql_service.MySQLStartupError):
                mysql_service.wait_for_database_connection(
                    time.monotonic() + 10,
                    connection_factory=factory,
                )
        factory.assert_called_once_with()
        sleep.assert_not_called()


class LoginDatabaseRetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as app_module

        cls.app_module = app_module
        cls.client = app_module.app.test_client()

    @staticmethod
    def connection(cursor):
        context = Mock()
        context.__enter__ = Mock(return_value=cursor)
        context.__exit__ = Mock(return_value=False)
        connection = Mock()
        connection.cursor.return_value = context
        return connection

    def test_login_reacquires_connection_after_query_disconnect(self):
        broken_cursor = Mock()
        broken_cursor.execute.side_effect = pymysql.err.OperationalError(
            2013, "lost connection"
        )
        healthy_cursor = Mock()
        healthy_cursor.fetchone.return_value = {
            "id": 1,
            "username": "retry-user",
            "email": "retry@example.com",
            "password_hash": "hash",
            "role": "user",
        }
        broken = self.connection(broken_cursor)
        healthy = self.connection(healthy_cursor)

        with patch.object(
            self.app_module,
            "get_db_connection",
            side_effect=[broken, healthy],
        ) as get_connection, patch.object(
            self.app_module.time, "sleep"
        ), patch.object(
            self.app_module, "password_hash_is_valid", return_value=True
        ), patch.object(
            self.app_module, "create_access_token", return_value="access"
        ), patch.object(
            self.app_module, "create_refresh_token", return_value="refresh"
        ):
            response = self.client.post(
                "/api/auth/login",
                json={"account": "retry-user", "password": "secret"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_connection.call_count, 2)
        broken.close.assert_called_once_with()
        healthy.close.assert_called_once_with()

    def test_login_does_not_retry_bad_database_credentials(self):
        with patch.object(
            self.app_module,
            "get_db_connection",
            side_effect=pymysql.err.OperationalError(1045, "access denied"),
        ) as get_connection, patch.object(self.app_module.time, "sleep") as sleep:
            response = self.client.post(
                "/api/auth/login",
                json={"account": "configuration-test", "password": "secret"},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(get_connection.call_count, 1)
        sleep.assert_not_called()

    def test_database_health_contract(self):
        cursor = Mock()
        connection = self.connection(cursor)
        with patch.object(
            self.app_module, "get_db_connection", return_value=connection
        ):
            response = self.client.get("/api/health/database")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(), {"ok": True, "database": "available"}
        )
        cursor.execute.assert_called_once_with("SELECT 1")


if __name__ == "__main__":
    unittest.main()
