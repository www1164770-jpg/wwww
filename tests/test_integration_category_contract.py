import unittest
from flask import Flask
from flask_jwt_extended import JWTManager
from test_site_search_v1 import SearchDatabase, SearchCursor, SearchConnection
from v1_routes import register_v1_routes


class LegacyCursor(SearchCursor):
    def execute(self, sql, params=None):
        super().execute(sql, params)
        if sql.startswith('SELECT id, name,') and 'FROM categories' in sql:
            self.rows = self.database.categories if 'WHERE 1=1' in sql else []


class LegacyConnection(SearchConnection):
    def cursor(self):
        return LegacyCursor(self.database)


class CategoryIntegrationTests(unittest.TestCase):
    def client(self, categories):
        database = SearchDatabase()
        database.categories = categories
        app = Flask(__name__)
        app.config.update(TESTING=True, JWT_SECRET_KEY='integration-test-key-long-enough-only')
        JWTManager(app)
        register_v1_routes(app, lambda: LegacyConnection(database))
        return app.test_client()

    def test_generated_public_code_can_filter_legacy_category(self):
        response = self.client([{'id':10,'name':'Test Resources','code':None}]).get('/api/sites/search?q=Vue&category=test_resources')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['data']['items'])

    def test_ambiguous_generated_code_is_rejected(self):
        response = self.client([{'id':10,'name':'未译甲','code':None},{'id':11,'name':'未译乙','code':None}]).get('/api/sites/search?q=Vue&category='+'category')
        self.assertEqual(response.status_code, 400)

    def test_explicit_different_code_does_not_gain_generated_alias(self):
        response = self.client([{'id':10,'name':'Test Resources','code':'real_code'}]).get('/api/sites/search?q=Vue&category=test_resources')
        self.assertEqual(response.status_code, 400)

