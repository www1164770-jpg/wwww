from __future__ import annotations

import unittest

from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from backend.crawler.db import (
    AnalysisResult,
    CrawlRun,
    CrawlTask,
    CrawlerSetting,
    OutboxEvent,
    WorkerHeartbeat,
    FetchResult,
    DiscoveredLink,
    IconAsset,
    RiskDecision,
)
from backend.crawler.queue.tasks import build_lease_query
from backend.crawler.outbox.service import build_outbox_lease_query
from tests.crawler.support import NOW


class MySQLSchemaContractTests(unittest.TestCase):
    def test_phase_one_through_three_models_compile_for_mysql_with_native_json_and_bigint_ids(
        self,
    ) -> None:
        compiled = {
            model.__tablename__: str(
                CreateTable(model.__table__).compile(dialect=mysql.dialect())
            ).upper()
            for model in (
                CrawlRun,
                CrawlTask,
                WorkerHeartbeat,
                CrawlerSetting,
                OutboxEvent,
                FetchResult,
                DiscoveredLink,
                AnalysisResult,
                RiskDecision,
                IconAsset,
            )
        }

        self.assertIn("BIGINT NOT NULL AUTO_INCREMENT", compiled["crawl_runs"])
        self.assertIn("PAYLOAD_JSON JSON", compiled["crawl_tasks"])
        self.assertIn("METADATA_JSON JSON", compiled["worker_heartbeats"])
        self.assertIn("PAYLOAD_JSON JSON", compiled["outbox_events"])
        self.assertIn(
            "UNIQUE (TASK_TYPE, ACTIVE_DEDUPE_KEY)",
            compiled["crawl_tasks"],
        )
        self.assertIn("REDIRECT_CHAIN JSON", compiled["fetch_results"])
        self.assertIn("BYTES_READ BIGINT", compiled["fetch_results"])
        self.assertIn("METADATA_JSON JSON", compiled["discovered_links"])
        self.assertIn("FOREIGNKEY(TASK_ID)", compiled["fetch_results"].replace(" ", ""))
        self.assertIn("TAGS_JSON JSON", compiled["analysis_results"])
        self.assertIn("EVIDENCE_HASHES_JSON JSON", compiled["analysis_results"])
        self.assertIn(
            "FOREIGNKEY(FETCH_RESULT_ID)",
            compiled["analysis_results"].replace(" ", ""),
        )
        self.assertIn("RULE_CODES_JSON JSON", compiled["risk_decisions"])
        self.assertIn(
            "FOREIGNKEY(ANALYSIS_RESULT_ID)",
            compiled["risk_decisions"].replace(" ", ""),
        )
        self.assertIn("CONTENT_HASH VARCHAR(64)", compiled["icon_assets"])
        self.assertIn(
            "FOREIGNKEY(FETCH_RESULT_ID)",
            compiled["icon_assets"].replace(" ", ""),
        )

    def test_task_lease_query_compiles_to_skip_locked_for_mysql(self) -> None:
        query = build_lease_query(
            task_types=["fetch_url"],
            now=NOW,
            limit=10,
        )

        sql = str(
            query.compile(
                dialect=mysql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        ).upper()

        self.assertIn("FOR UPDATE SKIP LOCKED", sql)
        self.assertIn("CRAWL_TASKS.STATUS = 'PENDING'", sql)
        self.assertIn("LIMIT 10", sql)
        self.assertNotIn("JOIN CRAWL_RUNS", sql)
        self.assertIn("EXISTS (SELECT CRAWL_RUNS.ID", sql)

    def test_outbox_lease_query_compiles_to_skip_locked_for_mysql(self) -> None:
        query = build_outbox_lease_query(now=NOW, limit=5)

        sql = str(
            query.compile(
                dialect=mysql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        ).upper()

        self.assertIn("FOR UPDATE SKIP LOCKED", sql)
        self.assertIn("OUTBOX_EVENTS.STATUS = 'PENDING'", sql)
        self.assertIn("LIMIT 5", sql)


if __name__ == "__main__":
    unittest.main()
