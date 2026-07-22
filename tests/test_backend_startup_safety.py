import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
PYTHON = sys.executable
UNREACHABLE_REDIS_URL = "redis://test-user:test-password@127.0.0.1:1/0"


def startup_environment():
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "cp1250"
    environment["REDIS_URL"] = UNREACHABLE_REDIS_URL
    environment["PYTHONPATH"] = str(BACKEND_DIR)
    return environment


class BackendStartupSafetyTests(unittest.TestCase):
    def test_redis_fallback_imports_under_cp1250_without_leaking_url(self):
        result = subprocess.run(
            [PYTHON, "-c", "import app; print('APP_IMPORT_OK')"],
            cwd=ROOT,
            env=startup_environment(),
            capture_output=True,
            text=True,
            timeout=20,
        )

        output = f"{result.stdout}\n{result.stderr}"
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("APP_IMPORT_OK", output)
        self.assertNotIn("UnicodeEncodeError", output)
        self.assertNotIn(UNREACHABLE_REDIS_URL, output)
        self.assertNotIn("test-password", output)

    def test_wsgi_exports_one_application_object(self):
        from backend.wsgi import app, application

        self.assertIs(app, application)
        self.assertTrue(hasattr(app, "route"))

    def test_wsgi_source_has_no_startup_side_effects(self):
        source = (BACKEND_DIR / "wsgi.py").read_text(encoding="utf-8")
        for forbidden in (
            "create_all",
            "drop_all",
            "sync",
            "app.run",
            "run_simple",
            "seed_data",
            "initialize_data",
        ):
            self.assertNotIn(forbidden, source)

    def test_flask_cli_loads_wsgi_routes_without_redis(self):
        result = subprocess.run(
            [PYTHON, "-m", "flask", "--app", "backend.wsgi:app", "routes"],
            cwd=ROOT,
            env=startup_environment(),
            capture_output=True,
            text=True,
            timeout=20,
        )

        output = f"{result.stdout}\n{result.stderr}"
        self.assertEqual(result.returncode, 0, output)
        self.assertIn("/api/ai/site-recommend", output)
        self.assertNotIn("UnicodeEncodeError", output)
        self.assertNotIn(UNREACHABLE_REDIS_URL, output)
        self.assertNotIn("test-password", output)


if __name__ == "__main__":
    unittest.main()
