import io
import logging
import logging.handlers
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from flask import Flask


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import app_extensions


class LoggingFallbackTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.original_app_handlers = list(self.app.logger.handlers)
        self.werkzeug_logger = logging.getLogger("werkzeug")
        self.original_werkzeug_handlers = list(self.werkzeug_logger.handlers)

    def tearDown(self):
        self._remove_new_handlers()

    def _remove_new_handlers(self):
        for logger, original_handlers in (
            (self.app.logger, self.original_app_handlers),
            (self.werkzeug_logger, self.original_werkzeug_handlers),
        ):
            for handler in list(logger.handlers):
                if handler not in original_handlers:
                    logger.removeHandler(handler)
                    handler.close()
            logger.handlers[:] = original_handlers

    def test_setup_logging_falls_back_to_console_when_log_directory_is_unavailable(self):
        captured_stderr = io.StringIO()

        with patch.object(
            app_extensions.os,
            "makedirs",
            side_effect=PermissionError(5, "Access is denied"),
        ), redirect_stderr(captured_stderr):
            result = app_extensions.setup_logging(self.app)
            self.app.logger.info("logging fallback works")

        self.assertIs(result, self.app)
        self.assertTrue(
            any(
                type(handler) is logging.StreamHandler
                for handler in self.app.logger.handlers
            )
        )
        self.assertFalse(
            any(
                isinstance(handler, logging.FileHandler)
                for handler in self.app.logger.handlers
            )
        )
        warning_output = captured_stderr.getvalue()
        self.assertIn("File logging unavailable; using console logging (PermissionError).", warning_output)
        self.assertNotIn("Access is denied", warning_output)
        self.assertNotIn("backend", warning_output)

    def test_setup_logging_keeps_file_logging_when_directory_is_available(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.object(
                app_extensions.os.path,
                "dirname",
                return_value=temporary_directory,
            ):
                result = app_extensions.setup_logging(self.app)
                self.app.logger.info("normal file logging works")
                self.app.logger.error("normal error file logging works")

            self.assertIs(result, self.app)
            file_handlers = [
                handler
                for handler in self.app.logger.handlers
                if isinstance(handler, logging.handlers.TimedRotatingFileHandler)
            ]
            self.assertEqual(len(file_handlers), 2)
            self.assertEqual(
                {Path(handler.baseFilename).name for handler in file_handlers},
                {"app.log", "error.log"},
            )
            self.assertEqual(
                {handler.level for handler in file_handlers},
                {logging.INFO, logging.ERROR},
            )
            console_handlers = [
                handler
                for handler in self.app.logger.handlers
                if type(handler) is logging.StreamHandler
            ]
            self.assertEqual(len(console_handlers), 1)
            self.assertEqual(console_handlers[0].level, logging.DEBUG)
            self._remove_new_handlers()


if __name__ == "__main__":
    unittest.main()
