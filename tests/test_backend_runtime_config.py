import json
import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
PROBE_PREFIX = "RUNTIME_CONFIG_PROBE="
DATABASE_ENV_KEYS = (
    "MYSQL_HOST",
    "MYSQL_PORT",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_DATABASE",
    "MYSQL_CHARSET",
    "DB_HOST",
    "DB_PORT",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
    "DB_CHARSET",
)
SENSITIVE_ENV_KEYS = (
    "FLASK_SECRET_KEY",
    "JWT_SECRET_KEY",
    "SECRET_KEY",
    "GITHUB_CLIENT_ID",
    "GITHUB_CLIENT_SECRET",
    "SMTP_AUTH_CODE",
    "SMTP_PASSWORD",
    "EMAIL_PASSWORD",
    "MAIL_PASSWORD",
    "MAIL_USERNAME",
    "REDIS_PASSWORD",
)


def run_runtime_probe(probe_source, timeout=30, **environment_overrides):
    environment = os.environ.copy()
    for key in DATABASE_ENV_KEYS + SENSITIVE_ENV_KEYS:
        environment.pop(key, None)
    environment.update(
        {
            "PYTHON_DOTENV_DISABLED": "1",
            "PYTHONIOENCODING": "utf-8",
            "APP_ENV": "development",
            "FLASK_ENV": "development",
            "REDIS_URL": "redis://127.0.0.1:1/0",
            "DB_HOST": "127.0.0.1",
            "DB_PORT": "3306",
            "DB_USER": "runtime_test_user",
            "DB_PASSWORD": "runtime_test_password",
            "DB_NAME": "runtime_test_database",
        }
    )
    environment.update(environment_overrides)

    source = textwrap.dedent(probe_source)
    result = subprocess.run(
        [sys.executable, "-c", source],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(
            "runtime probe failed without exposing environment values:\n"
            f"returncode={result.returncode}\n"
            f"stderr={result.stderr[-2000:]}"
        )

    probe_lines = [
        line for line in result.stdout.splitlines() if line.startswith(PROBE_PREFIX)
    ]
    if len(probe_lines) != 1:
        raise AssertionError("runtime probe did not return exactly one result marker")
    return json.loads(probe_lines[0][len(PROBE_PREFIX) :])


class BackendRuntimeConfigTests(unittest.TestCase):
    def test_database_uri_encodes_credentials_and_forces_utf8mb4(self):
        special_username = "runtime@test:/#?%"
        special_password = "test@pass:/#?%"
        probe = run_runtime_probe(
            """
            import json
            import os
            from sqlalchemy.engine import make_url
            import app
            import db_pool

            uri = app.app.config["SQLALCHEMY_DATABASE_URI"]
            parsed = make_url(uri)
            payload = {
                "username_round_trips": parsed.username == os.environ["DB_USER"],
                "password_round_trips": parsed.password == os.environ["DB_PASSWORD"],
                "plain_username_absent": os.environ["DB_USER"] not in uri,
                "plain_password_absent": os.environ["DB_PASSWORD"] not in uri,
                "sqlalchemy_charset": parsed.query.get("charset"),
                "manual_charset": app.DB_CONFIG["charset"],
                "pool_charset": db_pool.POOL_CONFIG["charset"],
            }
            print("RUNTIME_CONFIG_PROBE=" + json.dumps(payload, sort_keys=True))
            """,
            DB_USER=special_username,
            DB_PASSWORD=special_password,
            MYSQL_CHARSET="latin1",
            DB_CHARSET="utf8",
        )

        self.assertTrue(probe["username_round_trips"])
        self.assertTrue(probe["password_round_trips"])
        self.assertTrue(probe["plain_username_absent"])
        self.assertTrue(probe["plain_password_absent"])
        self.assertEqual(probe["sqlalchemy_charset"], "utf8mb4")
        self.assertEqual(probe["manual_charset"], "utf8mb4")
        self.assertEqual(probe["pool_charset"], "utf8mb4")

    def test_health_routes_separate_liveness_from_database_readiness(self):
        probe = run_runtime_probe(
            """
            import json
            from unittest.mock import patch
            import app

            client = app.app.test_client()
            with patch.object(
                app,
                "get_db_connection",
                side_effect=AssertionError("liveness must not access the database"),
            ):
                liveness = client.get("/api/health")

            class Cursor:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_value, traceback):
                    return False

                def execute(self, statement):
                    if statement != "SELECT 1":
                        raise AssertionError("unexpected database health query")

                def fetchone(self):
                    return (1,)

            class Connection:
                def __init__(self):
                    self.closed = False

                def cursor(self):
                    return Cursor()

                def close(self):
                    self.closed = True

            connection = Connection()
            with patch.object(app, "get_db_connection", return_value=connection):
                database_ok = client.get("/api/health/db")

            private_error = "private-database-detail"
            with patch.object(
                app,
                "get_db_connection",
                side_effect=RuntimeError(private_error),
            ):
                database_error = client.get("/api/health/db")

            payload = {
                "liveness_status": liveness.status_code,
                "liveness_payload": liveness.get_json(),
                "database_ok_status": database_ok.status_code,
                "database_ok_payload": database_ok.get_json(),
                "connection_closed": connection.closed,
                "database_error_status": database_error.status_code,
                "database_error_payload": database_error.get_json(),
                "private_error_exposed": private_error in database_error.get_data(as_text=True),
            }
            print("RUNTIME_CONFIG_PROBE=" + json.dumps(payload, sort_keys=True))
            """
        )

        self.assertEqual(probe["liveness_status"], 200)
        self.assertEqual(probe["liveness_payload"]["data"]["status"], "ok")
        self.assertEqual(probe["database_ok_status"], 200)
        self.assertEqual(probe["database_ok_payload"]["data"]["database"], "ok")
        self.assertTrue(probe["connection_closed"])
        self.assertEqual(probe["database_error_status"], 503)
        self.assertEqual(probe["database_error_payload"]["data"]["database"], "unavailable")
        self.assertFalse(probe["private_error_exposed"])

    def test_cors_uses_explicit_origins_and_rejects_wildcards_with_credentials(self):
        probe = run_runtime_probe(
            """
            import json
            import app

            client = app.app.test_client()

            def allowed_origin(origin):
                response = client.options(
                    "/api/health",
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "GET",
                    },
                )
                return response.headers.get("Access-Control-Allow-Origin")

            payload = {
                "configured_origins": app.get_cors_origins(),
                "local_origin_header": allowed_origin("http://localhost:5173"),
                "production_origin_header": allowed_origin("https://app.example.test"),
                "admin_origin_header": allowed_origin("https://admin.example.test"),
                "untrusted_origin_header": allowed_origin("https://untrusted.example.test"),
            }
            print("RUNTIME_CONFIG_PROBE=" + json.dumps(payload, sort_keys=True))
            """,
            FRONTEND_URL="*",
            CORS_ALLOWED_ORIGINS=(
                " https://app.example.test/, https://admin.example.test , , * "
            ),
        )

        origins = probe["configured_origins"]
        self.assertIn("https://app.example.test", origins)
        self.assertIn("https://admin.example.test", origins)
        self.assertNotIn("*", origins)
        self.assertEqual(probe["local_origin_header"], "http://localhost:5173")
        self.assertEqual(
            probe["production_origin_header"], "https://app.example.test"
        )
        self.assertEqual(
            probe["admin_origin_header"], "https://admin.example.test"
        )
        self.assertIsNone(probe["untrusted_origin_header"])

    def test_cors_covers_vite_ipv4_and_ipv6_origins_on_home_api_routes(self):
        origins = (
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://[::1]:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://[::1]:5174",
        )
        probe = run_runtime_probe(
            """
            import json
            from flask import Flask, jsonify
            import app

            cors_app = Flask("cors-probe")
            app.configure_cors(cors_app, app.LOCAL_VITE_ORIGINS)

            @cors_app.get("/api/categories")
            def api_response():
                return jsonify({"code": 200, "data": []})

            cors_app.add_url_rule(
                "/api/sites/recommend",
                endpoint="recommend_response",
                view_func=api_response,
                methods=["GET"],
            )
            client = cors_app.test_client()
            results = []
            for origin in %(origins)r:
                for path in ("/api/categories", "/api/sites/recommend"):
                    get_response = client.get(path, headers={"Origin": origin})
                    options_response = client.options(
                        path,
                        headers={
                            "Origin": origin,
                            "Access-Control-Request-Method": "GET",
                            "Access-Control-Request-Headers": "authorization, content-type",
                        },
                    )
                    for method, response in (("GET", get_response), ("OPTIONS", options_response)):
                        results.append({
                            "origin": origin,
                            "path": path,
                            "method": method,
                            "status": response.status_code,
                            "allow_origin": response.headers.get("Access-Control-Allow-Origin"),
                            "allow_credentials": response.headers.get("Access-Control-Allow-Credentials"),
                            "allow_origin_values": response.headers.getlist("Access-Control-Allow-Origin"),
                        })

            untrusted = client.options(
                "/api/categories",
                headers={"Origin": "https://untrusted.example.test", "Access-Control-Request-Method": "GET"},
            )
            print("RUNTIME_CONFIG_PROBE=" + json.dumps({
                "results": results,
                "untrusted_allow_origin": untrusted.headers.get("Access-Control-Allow-Origin"),
            }, sort_keys=True))
            """ % {"origins": origins},
            FRONTEND_URL="",
            CORS_ALLOWED_ORIGINS="",
        )

        self.assertIsNone(probe["untrusted_allow_origin"])
        self.assertEqual(len(probe["results"]), len(origins) * 4)
        for result in probe["results"]:
            with self.subTest(**result):
                self.assertEqual(result["status"], 200)
                self.assertEqual(result["allow_origin"], result["origin"])
                self.assertEqual(result["allow_credentials"], "true")
                self.assertEqual(result["allow_origin_values"], [result["origin"]])

    def test_production_cors_does_not_default_to_local_vite_origins(self):
        probe = run_runtime_probe(
            """
            import json
            import app

            response = app.app.test_client().options(
                "/api/categories",
                headers={"Origin": "http://[::1]:5173", "Access-Control-Request-Method": "GET"},
            )
            print("RUNTIME_CONFIG_PROBE=" + json.dumps({
                "origins": app.get_cors_origins(),
                "allow_origin": response.headers.get("Access-Control-Allow-Origin"),
            }, sort_keys=True))
            """,
            APP_ENV="production",
            FLASK_ENV="production",
            FRONTEND_URL="",
            CORS_ALLOWED_ORIGINS="",
            FLASK_SECRET_KEY="production-test-flask-secret",
            JWT_SECRET_KEY="production-test-jwt-secret",
        )

        self.assertEqual(probe["origins"], [])
        self.assertIsNone(probe["allow_origin"])


if __name__ == "__main__":
    unittest.main()
