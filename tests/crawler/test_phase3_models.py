from __future__ import annotations

import unittest

from sqlalchemy import inspect

from backend.crawler.db import AnalysisResult, IconAsset, RiskDecision
from backend.crawler.db.migration import _migration_statements
from tests.crawler.support import make_sqlite_engine


class PhaseThreeModelTests(unittest.TestCase):
    def test_phase_three_tables_have_stable_uids_constraints_and_foreign_keys(self) -> None:
        engine = make_sqlite_engine()
        try:
            inspector = inspect(engine)
            table_names = set(inspector.get_table_names())
            self.assertTrue(
                {"analysis_results", "risk_decisions", "icon_assets"}.issubset(table_names)
            )
            for table in ("analysis_results", "risk_decisions", "icon_assets"):
                self.assertTrue(inspector.get_foreign_keys(table))
                unique_columns = {
                    tuple(item["column_names"])
                    for item in inspector.get_unique_constraints(table)
                }
                uid = {
                    "analysis_results": "analysis_uid",
                    "risk_decisions": "decision_uid",
                    "icon_assets": "asset_uid",
                }[table]
                self.assertIn((uid,), unique_columns)
            analysis_unique = {
                tuple(item["column_names"])
                for item in inspector.get_unique_constraints("analysis_results")
            }
            self.assertIn(("fetch_result_id", "analysis_version"), analysis_unique)
        finally:
            engine.dispose()

    def test_phase_three_migration_is_forward_only(self) -> None:
        from backend.crawler.db.migration import MIGRATION_DIR

        path = MIGRATION_DIR / "0003_analysis_risk_assets.sql"
        self.assertTrue(path.is_file())
        statements = _migration_statements(path)
        self.assertGreaterEqual(len(statements), 3)
        normalized = "\n".join(statements).upper()
        self.assertIn("CREATE TABLE IF NOT EXISTS ANALYSIS_RESULTS", normalized)
        self.assertIn("CREATE TABLE IF NOT EXISTS RISK_DECISIONS", normalized)
        self.assertIn("CREATE TABLE IF NOT EXISTS ICON_ASSETS", normalized)
        self.assertNotIn("NAV_SITE", normalized)
        self.assertNotIn("DROP ", normalized)

    def test_models_are_exported(self) -> None:
        self.assertEqual(AnalysisResult.__tablename__, "analysis_results")
        self.assertEqual(RiskDecision.__tablename__, "risk_decisions")
        self.assertEqual(IconAsset.__tablename__, "icon_assets")


if __name__ == "__main__":
    unittest.main()
