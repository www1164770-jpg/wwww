from __future__ import annotations

from datetime import time
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.crawler.config import CrawlerSettings
from backend.crawler.observability.json_logging import (
    configure_crawler_logging,
    log_event,
    redact_sensitive,
    sanitize_error_message,
)


REQUIRED_LOG_FIELDS = {
    "timestamp",
    "level",
    "component",
    "event",
    "worker_id",
    "run_uid",
    "task_uid",
    "duration_ms",
    "error_code",
}


def settings_for(log_root: Path) -> CrawlerSettings:
    return CrawlerSettings(
        database_url=None,
        icon_root=log_root.parent / "icons",
        log_root=log_root,
        worker_id="worker-a",
        lease_seconds=300,
        max_attempts=3,
        nightly_target=3000,
        start_time=time(1, 0),
        stop_time=time(5, 0),
    )


class RedactionTests(unittest.TestCase):
    def test_recursive_sensitive_keys_body_and_pii_are_redacted(self) -> None:
        value = {
            "safe": "visible",
            "Authorization": "Bearer private-token",
            "nested": {
                "Cookie": "private-cookie",
                "password": "private-password",
                "email": "person@example.test",
                "response_body": "<html>private body</html>",
            },
            "list": [{"api-key": "private-key"}],
        }

        redacted = redact_sensitive(value)
        text = str(redacted)

        self.assertIn("visible", text)
        for private_value in (
            "private-token",
            "private-cookie",
            "private-password",
            "person@example.test",
            "private body",
            "private-key",
        ):
            self.assertNotIn(private_value, text)
        self.assertGreaterEqual(text.count("[REDACTED]"), 6)

    def test_database_url_password_is_redacted_even_under_safe_key(self) -> None:
        redacted = redact_sensitive(
            "mysql+pymysql://crawler:private-password@localhost/zhihui_crawler"
        )

        self.assertIn("crawler:", redacted)
        self.assertIn("@localhost", redacted)
        self.assertNotIn("private-password", redacted)

    def test_error_message_is_one_line_bounded_and_secret_free(self) -> None:
        message = (
            "Authorization: Bearer private-token; password=private-password "
            + ("x" * 2000)
            + "\n<html>full page body</html>"
        )

        sanitized = sanitize_error_message(message, max_length=200)

        self.assertLessEqual(len(sanitized), 200)
        self.assertNotIn("private-token", sanitized)
        self.assertNotIn("private-password", sanitized)
        self.assertNotIn("full page body", sanitized)
        self.assertNotIn("\n", sanitized)

    def test_html_error_body_is_omitted(self) -> None:
        self.assertEqual(
            sanitize_error_message("<!doctype html><html>private</html>"),
            "[response body omitted]",
        )


class StructuredLoggingTests(unittest.TestCase):
    def test_log_event_emits_one_json_line_with_required_context(self) -> None:
        output = io.StringIO()
        logger = configure_crawler_logging(
            settings_for(Path("unused")),
            component="queue",
            stream=output,
        )

        log_event(
            logger,
            "task_leased",
            worker_id="worker-a",
            run_uid="run-1",
            task_uid="task-1",
            duration_ms=12,
            error_code=None,
            count=2,
        )

        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(REQUIRED_LOG_FIELDS - set(record), set())
        self.assertEqual(record["level"], "INFO")
        self.assertEqual(record["component"], "queue")
        self.assertEqual(record["event"], "task_leased")
        self.assertEqual(record["worker_id"], "worker-a")
        self.assertEqual(record["duration_ms"], 12)
        self.assertEqual(record["details"], {"count": 2})

    def test_sensitive_details_and_full_payload_never_reach_json(self) -> None:
        output = io.StringIO()
        logger = configure_crawler_logging(
            settings_for(Path("unused")),
            component="outbox",
            stream=output,
        )

        log_event(
            logger,
            "event_failed",
            error_code="password=private-error-code",
            payload={
                "Authorization": "private-token",
                "body": "complete sensitive payload",
            },
            database_url=(
                "mysql+pymysql://crawler:private-password@localhost/"
                "zhihui_crawler"
            ),
        )

        text = output.getvalue()
        json.loads(text)
        self.assertNotIn("private-token", text)
        self.assertNotIn("complete sensitive payload", text)
        self.assertNotIn("private-password", text)
        self.assertNotIn("private-error-code", text)
        self.assertEqual(json.loads(text)["error_code"], "invalid_error_code")
        self.assertGreaterEqual(text.count("[REDACTED]"), 2)

    def test_default_configuration_writes_jsonl_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_root = Path(temporary_directory) / "crawler-logs"
            logger = configure_crawler_logging(
                settings_for(log_root),
                component="cli",
            )
            try:
                log_event(logger, "db_checked")
                for handler in logger.handlers:
                    handler.flush()

                text = (log_root / "crawler.jsonl").read_text(encoding="utf-8")
                self.assertEqual(json.loads(text)["event"], "db_checked")
            finally:
                for handler in list(logger.handlers):
                    logger.removeHandler(handler)
                    handler.close()

    def test_unavailable_log_directory_falls_back_without_private_details(
        self,
    ) -> None:
        fallback = io.StringIO()
        with patch.object(
            Path,
            "mkdir",
            side_effect=PermissionError("private filesystem path"),
        ):
            logger = configure_crawler_logging(
                settings_for(Path("private/path")),
                component="cli",
                stream=fallback,
                force_file_attempt=True,
            )

        text = fallback.getvalue()
        record = json.loads(text)
        self.assertEqual(record["event"], "logging_fallback")
        self.assertEqual(record["error_code"], "PermissionError")
        self.assertNotIn("private filesystem path", text)
        self.assertNotIn("private/path", text)


if __name__ == "__main__":
    unittest.main()
