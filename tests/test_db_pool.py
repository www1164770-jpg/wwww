import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import db_pool


class DatabasePoolTests(unittest.TestCase):
    def test_checkout_reconnects_before_returning_connection(self):
        class Connection:
            def __init__(self):
                self.ping_calls = []

            def ping(self, **kwargs):
                self.ping_calls.append(kwargs)

            def close(self):
                raise AssertionError("healthy connection should not be closed")

        class Pool:
            def __init__(self, connection):
                self.connection_value = connection

            def connection(self):
                return self.connection_value

        connection = Connection()
        with patch.object(db_pool, "get_pool", return_value=Pool(connection)):
            result = db_pool.get_connection()

        self.assertIs(result, connection)
        self.assertEqual(connection.ping_calls, [{"reconnect": True}])

    def test_failed_checkout_is_returned_to_the_pool(self):
        class Connection:
            def __init__(self):
                self.closed = False

            def ping(self, **_kwargs):
                raise OSError("connection dropped")

            def close(self):
                self.closed = True

        class Pool:
            def __init__(self, connection):
                self.connection_value = connection

            def connection(self):
                return self.connection_value

        connection = Connection()
        with patch.object(db_pool, "get_pool", return_value=Pool(connection)):
            with self.assertRaises(OSError):
                db_pool.get_connection()

        self.assertTrue(connection.closed)
