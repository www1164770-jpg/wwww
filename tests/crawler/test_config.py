from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from datetime import time
import unittest

from backend.crawler.config import CrawlerConfigError, CrawlerSettings


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"


class CrawlerSettingsTests(unittest.TestCase):
    def test_defaults_do_not_require_a_database_url(self) -> None:
        settings = CrawlerSettings.from_env({})

        self.assertIsNone(settings.database_url)
        self.assertEqual(
            settings.icon_root,
            ROOT_DIR / "backend" / "data" / "crawler" / "icons",
        )
        self.assertEqual(
            settings.log_root,
            ROOT_DIR / "backend" / "data" / "crawler" / "logs",
        )
        self.assertEqual(settings.lease_seconds, 300)
        self.assertEqual(settings.max_attempts, 3)
        self.assertEqual(settings.nightly_target, 3000)
        self.assertEqual(settings.start_time, time(1, 0))
        self.assertEqual(settings.stop_time, time(5, 0))
        self.assertTrue(settings.worker_id)

    def test_crawler_cli_mode_requires_the_independent_database_url(self) -> None:
        with self.assertRaisesRegex(CrawlerConfigError, "CRAWLER_DATABASE_URL"):
            CrawlerSettings.from_env({}, require_database=True)

    def test_all_environment_values_are_parsed_without_formal_database_fallback(
        self,
    ) -> None:
        settings = CrawlerSettings.from_env(
            {
                "CRAWLER_DATABASE_URL": "mysql+pymysql://crawler.example.invalid/test",
                "CRAWLER_ICON_ROOT": "var/icons",
                "CRAWLER_LOG_ROOT": "var/logs",
                "CRAWLER_WORKER_ID": "worker-a",
                "CRAWLER_LEASE_SECONDS": "45",
                "CRAWLER_MAX_ATTEMPTS": "7",
                "CRAWLER_NIGHTLY_TARGET": "123",
                "CRAWLER_START_TIME": "02:15",
                "CRAWLER_STOP_TIME": "04:45",
                "MYSQL_DATABASE": "must_not_be_used",
                "DB_NAME": "must_not_be_used_either",
            }
        )

        self.assertEqual(
            settings.database_url,
            "mysql+pymysql://crawler.example.invalid/test",
        )
        self.assertEqual(settings.icon_root, ROOT_DIR / "var" / "icons")
        self.assertEqual(settings.log_root, ROOT_DIR / "var" / "logs")
        self.assertEqual(settings.worker_id, "worker-a")
        self.assertEqual(settings.lease_seconds, 45)
        self.assertEqual(settings.max_attempts, 7)
        self.assertEqual(settings.nightly_target, 123)
        self.assertEqual(settings.start_time, time(2, 15))
        self.assertEqual(settings.stop_time, time(4, 45))

    def test_absolute_runtime_paths_remain_absolute(self) -> None:
        absolute_path = (ROOT_DIR / "outside-default").resolve()

        settings = CrawlerSettings.from_env(
            {
                "CRAWLER_ICON_ROOT": str(absolute_path),
                "CRAWLER_LOG_ROOT": str(absolute_path),
            }
        )

        self.assertEqual(settings.icon_root, absolute_path)
        self.assertEqual(settings.log_root, absolute_path)

    def test_non_positive_integer_configuration_is_rejected(self) -> None:
        for key, value in (
            ("CRAWLER_LEASE_SECONDS", "0"),
            ("CRAWLER_MAX_ATTEMPTS", "-1"),
            ("CRAWLER_NIGHTLY_TARGET", "not-a-number"),
        ):
            with self.subTest(key=key, value=value):
                with self.assertRaisesRegex(CrawlerConfigError, key):
                    CrawlerSettings.from_env({key: value})

    def test_invalid_or_reversed_time_window_is_rejected(self) -> None:
        for environment in (
            {"CRAWLER_START_TIME": "1am"},
            {"CRAWLER_STOP_TIME": "24:00"},
            {
                "CRAWLER_START_TIME": "05:00",
                "CRAWLER_STOP_TIME": "01:00",
            },
            {
                "CRAWLER_START_TIME": "05:00",
                "CRAWLER_STOP_TIME": "05:00",
            },
        ):
            with self.subTest(environment=environment):
                with self.assertRaises(CrawlerConfigError):
                    CrawlerSettings.from_env(environment)

    def test_blank_worker_id_is_rejected(self) -> None:
        with self.assertRaisesRegex(CrawlerConfigError, "CRAWLER_WORKER_ID"):
            CrawlerSettings.from_env({"CRAWLER_WORKER_ID": "   "})

    def test_existing_backend_import_does_not_require_crawler_configuration(
        self,
    ) -> None:
        environment = os.environ.copy()
        environment.pop("CRAWLER_DATABASE_URL", None)
        environment.update(
            {
                "PYTHON_DOTENV_DISABLED": "1",
                "DB_HOST": "127.0.0.1",
                "DB_PORT": "3306",
                "DB_USER": "crawler_import_test",
                "DB_PASSWORD": "crawler_import_test",
                "DB_NAME": "crawler_import_test",
                "REDIS_URL": "redis://127.0.0.1:1/0",
            }
        )

        result = subprocess.run(
            [sys.executable, "-c", "import app; print('imported')"],
            cwd=BACKEND_DIR,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr[-1000:])
        self.assertIn("imported", result.stdout)


if __name__ == "__main__":
    unittest.main()
