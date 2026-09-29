"""Verify Docker startup never initializes an existing database."""

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
spec = importlib.util.spec_from_file_location(
    "docker_entrypoint", BACKEND / "docker-entrypoint.py"
)
entrypoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entrypoint)


class DockerEntrypointTests(unittest.TestCase):
    def check_startup(self, first_table, seed_failure=False):
        connection = MagicMock()
        cursor = connection.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = first_table
        application, initializer = MagicMock(), MagicMock()
        if seed_failure:
            initializer.run.side_effect = RuntimeError("seed failed")
        with (
            patch.object(entrypoint, "validate_database_config", return_value={}),
            patch.object(entrypoint, "get_database_config", return_value={}),
            patch.object(entrypoint.pymysql, "connect", return_value=connection),
            patch.dict(sys.modules, {"app": application, "init_db": initializer}),
            patch.object(entrypoint.os, "execv") as execute,
        ):
            if seed_failure:
                with self.assertRaisesRegex(RuntimeError, "seed failed"):
                    entrypoint.main()
                execute.assert_not_called()
            else:
                entrypoint.main()
                execute.assert_called_once_with(
                    sys.executable, [sys.executable, "backend/app.py"]
                )
        cursor.execute.assert_called_once_with("SHOW TABLES")
        return application, initializer

    def test_existing_database_is_not_initialized(self):
        app, seed = self.check_startup(("users",))
        app.initialize_database.assert_not_called()
        seed.run.assert_not_called()

    def test_empty_database_uses_existing_initializers(self):
        app, seed = self.check_startup(None)
        app.initialize_database.assert_called_once_with()
        seed.run.assert_called_once_with()

    def test_failed_initialization_does_not_start_server(self):
        self.check_startup(None, seed_failure=True)


if __name__ == "__main__":
    unittest.main()
