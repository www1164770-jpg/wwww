import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
VERCEL_CONFIG_PATH = ROOT_DIR / "vercel.json"
FRONTEND_DIR = ROOT_DIR / "backend" / "frontend"
REQUIRED_RUNTIME_PACKAGES = {
    "authing",
    "authlib",
    "dbutils",
    "feedparser",
    "flask",
    "flask-apscheduler",
    "flask-bcrypt",
    "flask-cors",
    "flask-jwt-extended",
    "flask-limiter",
    "flask-sqlalchemy",
    "meilisearch",
    "pyjwt",
    "pymysql",
    "python-dotenv",
    "redis",
    "requests",
    "sqlalchemy",
    "werkzeug",
    "websockets",
}


def load_vercel_config():
    return json.loads(VERCEL_CONFIG_PATH.read_text(encoding="utf-8"))


def normalize_requirement(line):
    name = line.strip().split(";", 1)[0]
    for separator in ("===", "==", ">=", "<=", "~=", "!=", ">", "<", "["):
        name = name.split(separator, 1)[0]
    return name.strip().lower().replace("_", "-")


def rewrite_matches(source, path):
    if source == path:
        return True
    if source == "/api/:path*":
        return path.startswith("/api/")
    if source == "/:path*":
        return path.startswith("/")
    return False


def resolve_rewrite(config, path):
    for rewrite in config["rewrites"]:
        if rewrite_matches(rewrite["source"], path):
            return rewrite["destination"]
    return None


class VercelConfigurationTests(unittest.TestCase):
    def test_vercel_json_is_modern_schema_valid_configuration(self):
        config = load_vercel_config()

        self.assertEqual(config["$schema"], "https://openapi.vercel.sh/vercel.json")
        self.assertNotIn("version", config)
        self.assertNotIn("builds", config)
        self.assertNotIn("routes", config)
        self.assertIn("rewrites", config)

    def test_frontend_build_uses_lockfile_and_repository_root_paths(self):
        config = load_vercel_config()

        self.assertTrue((FRONTEND_DIR / "package-lock.json").is_file())
        self.assertEqual(
            config["installCommand"],
            "npm ci --prefix backend/frontend",
        )
        self.assertEqual(
            config["buildCommand"],
            "npm run build --prefix backend/frontend",
        )
        self.assertEqual(config["outputDirectory"], "backend/frontend/dist")

    def test_api_rewrites_precede_spa_fallback_and_cover_root_api(self):
        config = load_vercel_config()
        rewrites = config["rewrites"]

        self.assertEqual(
            rewrites[:2],
            [
                {"source": "/api", "destination": "/api/index.py"},
                {"source": "/api/:path*", "destination": "/api/index.py"},
            ],
        )
        self.assertEqual(
            rewrites[-1],
            {"source": "/:path*", "destination": "/index.html"},
        )

        for path in (
            "/api",
            "/api/",
            "/api/health",
            "/api/health/db",
            "/api/sites/recommend",
            "/api/auth/me",
        ):
            with self.subTest(path=path):
                self.assertEqual(resolve_rewrite(config, path), "/api/index.py")

    def test_non_api_application_routes_use_spa_fallback(self):
        config = load_vercel_config()

        for path in (
            "/login",
            "/register",
            "/questionnaire",
            "/categories",
            "/profile",
            "/favorites",
            "/admin/dashboard",
        ):
            with self.subTest(path=path):
                self.assertEqual(resolve_rewrite(config, path), "/index.html")

    def test_python_function_excludes_only_non_runtime_content(self):
        config = load_vercel_config()
        function_config = config["functions"]["api/index.py"]
        excluded = function_config["excludeFiles"]

        for fragment in (
            "backend/frontend/node_modules",
            "backend/frontend/dist",
            ".venv",
            "tests",
            ".git",
            ".claude",
            "docs/superpowers",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, excluded)

        self.assertNotIn("maxDuration", function_config)
        self.assertNotIn("backend/app.py", excluded)
        self.assertNotIn("backend/db_pool.py", excluded)

    def test_runtime_requirements_match_backend_imports(self):
        lines = [
            line.strip()
            for line in (ROOT_DIR / "requirements.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        packages = {normalize_requirement(line) for line in lines}

        self.assertEqual(packages, REQUIRED_RUNTIME_PACKAGES)
        self.assertNotIn("pytest", packages)
        self.assertIn("websockets>=13.1,<14.0", lines)
        self.assertFalse(any(line.startswith(("-e ", "git+", "file:")) for line in lines))
        self.assertEqual(len(packages), len(lines), "requirements contain duplicates")

    def test_vercelignore_blocks_local_artifacts_but_keeps_runtime_sources(self):
        lines = {
            line.strip().replace("\\", "/")
            for line in (ROOT_DIR / ".vercelignore")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        for required in (
            ".git",
            ".github",
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            "backend/frontend/node_modules",
            "backend/frontend/dist",
            ".env",
            ".env.*",
            ".claude",
            "docs/superpowers",
            "tests",
        ):
            with self.subTest(required=required):
                self.assertIn(required, lines)

        self.assertNotIn("api", lines)
        self.assertNotIn("backend", lines)
        self.assertNotIn("backend/frontend", lines)

    def test_deployment_document_covers_repository_root_and_operations(self):
        document = (ROOT_DIR / "DEPLOY_VERCEL.md").read_text(encoding="utf-8")

        for expected in (
            "仓库根目录",
            "不要设置为 `backend/frontend`",
            "VITE_API_BASE_URL",
            "保持未设置",
            "DB_HOST",
            "不能使用 `localhost`",
            "Redis",
            "Production",
            "Preview",
            "Authing",
            "/authing/callback",
            "GET /api/health",
            "GET /api/health/db",
            "GET /api/sites/recommend",
            "GET /api/auth/me",
            "回滚",
            "Function Logs",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, document)


class VercelFunctionImportTests(unittest.TestCase):
    def test_function_import_has_no_server_database_or_scheduler_side_effects(self):
        script = r'''
import json
import threading
from unittest.mock import patch

from flask import Flask
from flask_apscheduler import APScheduler
from flask_sqlalchemy import SQLAlchemy
import pymysql
import redis

events = []
threads_before = {thread.ident for thread in threading.enumerate()}
original_thread_start = threading.Thread.start

def record(name, result=None):
    def replacement(*args, **kwargs):
        events.append(name)
        return result
    return replacement

def record_thread_start(thread, *args, **kwargs):
    events.append(
        f"thread.start:{thread.name}:{type(thread).__module__}.{type(thread).__name__}"
    )
    return original_thread_start(thread, *args, **kwargs)

with (
    patch.object(threading.Thread, "start", record_thread_start),
    patch.object(Flask, "run", record("app.run")),
    patch.object(APScheduler, "start", record("scheduler.start")),
    patch.object(SQLAlchemy, "create_all", record("db.create_all")),
    patch.object(pymysql, "connect", record("pymysql.connect")),
    patch.object(redis.Redis, "ping", return_value=True),
):
    from api.index import app

threads_after = {
    thread.ident
    for thread in threading.enumerate()
    if thread.ident not in threads_before
}
required_routes = {
    "/api/health",
    "/api/health/db",
    "/api/auth/login",
    "/api/auth/me",
    "/api/questionnaire/submit",
    "/api/sites/recommend",
}
actual_routes = {rule.rule for rule in app.url_map.iter_rules()}
print("VERCEL_IMPORT_RESULT=" + json.dumps({
    "is_flask": isinstance(app, Flask),
    "events": events,
    "new_thread_count": len(threads_after),
    "missing_routes": sorted(required_routes - actual_routes),
}))
'''
        environment = os.environ.copy()
        environment.update(
            {
                "APP_ENV": "testing",
                "FLASK_ENV": "testing",
                "VERCEL": "1",
                "DB_HOST": "invalid.test",
                "DB_NAME": "test_db",
                "DB_USER": "test_user",
                "DB_PASSWORD": "test_password",
                "FLASK_SECRET_KEY": "test_flask_secret",
                "JWT_SECRET_KEY": "test_jwt_secret",
                "REDIS_URL": "redis://invalid.test:6379/0",
            }
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT_DIR,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result_line = next(
            (
                line
                for line in completed.stdout.splitlines()
                if line.startswith("VERCEL_IMPORT_RESULT=")
            ),
            None,
        )
        self.assertIsNotNone(result_line, completed.stdout)
        result = json.loads(result_line.split("=", 1)[1])
        self.assertTrue(result["is_flask"])
        self.assertEqual(result["events"], [])
        self.assertEqual(result["new_thread_count"], 0)
        self.assertEqual(result["missing_routes"], [])


if __name__ == "__main__":
    unittest.main()
