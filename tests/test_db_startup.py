import ast
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
APP_PATH = BACKEND_DIR / "app.py"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import db_pool


class DatabaseStartupTests(unittest.TestCase):
    def test_dbutils_pool_is_lazy_and_singleton(self):
        original_pool = db_pool._pool
        db_pool._pool = None
        sentinel_pool = object()
        try:
            with patch.object(db_pool, "PooledDB", return_value=sentinel_pool) as factory:
                first = db_pool.get_pool()
                second = db_pool.get_pool()

            self.assertIs(first, sentinel_pool)
            self.assertIs(second, sentinel_pool)
            factory.assert_called_once_with(**db_pool.POOL_CONFIG)
        finally:
            db_pool._pool = original_pool

    def test_dbutils_pool_uses_conservative_limits_and_connection_checks(self):
        config = db_pool.POOL_CONFIG

        self.assertLessEqual(config["maxconnections"], 5)
        self.assertEqual(config["mincached"], 0)
        self.assertLessEqual(config["maxcached"], 5)
        self.assertTrue(config["blocking"])
        self.assertGreaterEqual(config["ping"], 1)

    def test_sqlalchemy_pool_uses_conservative_recycling_options(self):
        import app as app_module

        options = app_module.app.config["SQLALCHEMY_ENGINE_OPTIONS"]
        for key in (
            "pool_pre_ping",
            "pool_recycle",
            "pool_size",
            "max_overflow",
            "pool_timeout",
        ):
            self.assertIn(key, options)
        self.assertTrue(options["pool_pre_ping"])
        self.assertGreater(options["pool_recycle"], 0)
        self.assertLessEqual(options["pool_recycle"], 300)
        self.assertLessEqual(options["pool_size"], 5)
        self.assertLessEqual(options["max_overflow"], 5)
        self.assertGreater(options["pool_timeout"], 0)

    def test_schema_initialization_is_not_a_module_import_side_effect(self):
        tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
        parents = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent

        create_all_calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            if (
                isinstance(function, ast.Attribute)
                and function.attr == "create_all"
                and isinstance(function.value, ast.Name)
                and function.value.id == "db"
            ):
                create_all_calls.append(node)

        self.assertEqual(len(create_all_calls), 1)
        ancestor = parents.get(create_all_calls[0])
        while ancestor is not None and not isinstance(ancestor, ast.FunctionDef):
            ancestor = parents.get(ancestor)
        self.assertIsNotNone(ancestor)
        self.assertEqual(ancestor.name, "initialize_database")

    def test_reloader_parent_skips_initialization_and_child_runs_it(self):
        import app as app_module

        self.assertTrue(hasattr(app_module, "should_initialize_database"))
        should_initialize = app_module.should_initialize_database

        self.assertTrue(should_initialize(debug=False, run_main=None))
        self.assertFalse(should_initialize(debug=True, run_main=None))
        self.assertTrue(should_initialize(debug=True, run_main="true"))

    def test_initialization_calls_create_all_once_and_surfaces_failures(self):
        import app as app_module

        self.assertTrue(hasattr(app_module, "initialize_database"))
        with patch.object(app_module.db, "create_all") as create_all:
            app_module.initialize_database()
        create_all.assert_called_once_with()

        with patch.object(
            app_module.db,
            "create_all",
            side_effect=RuntimeError("schema initialization failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "schema initialization failed"):
                app_module.initialize_database()


if __name__ == "__main__":
    unittest.main()
