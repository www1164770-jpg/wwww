import sys
import unittest
from pathlib import Path

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from v1_routes import register_v1_routes


class ObservationCursor:
    def __init__(self, database):
        self.database = database
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split())
        self.database.statements.append(normalized)
        self.rows = []
        if "FROM (SELECT * FROM users WHERE username=%s OR email=%s)" in normalized:
            identity = str((params or [""])[0])
            self.rows = [{"id": 1, "username": identity, "email": f"{identity}@example.test", "role": "admin" if identity == "admin" else "user", "deleted_at": None}]
        elif "SUM(CASE WHEN w.id IS NULL" in normalized:
            self.rows = [{"total_events": 0, "impressions": 0, "clicks": 0, "favorites": 0, "repeat_visits": 0, "invalid_websites": 0, "invalid_users": 0, "invalid_event_types": 0, "missing_batch_id": 0, "missing_session_id": 0, "personalized_missing_source": 0}]
        elif "FROM ( SELECT COUNT(*) - 1 AS duplicate_count" in normalized:
            self.rows = [{"count": 0}]
        elif "repeat_visit' AND EXISTS" in normalized:
            self.rows = [{"count": 0}]
        elif "AS qualifying_occupations" in normalized:
            self.rows = [{"qualifying_occupations": 0}]
        elif "AS qualifying_profiles" in normalized:
            self.rows = [{"qualifying_profiles": 0}]
        elif "COUNT(DISTINCT e.recommendation_batch_id) AS batches" in normalized:
            self.rows = [{"batches": 0, "batch_users": 0, "first_event_at": None, "observed_days": 0}]
        elif normalized.startswith("INSERT INTO recommendation_observation_snapshots"):
            keys = ("snapshot_id", "algorithm_version", "lookback_days", "exclude_test_users", "captured_by_user_id", "summary_json", "data_quality_json", "readiness_json", "match_score_buckets_json", "primary_need_metrics_json", "tag_metrics_json", "personalization_metrics_json")
            self.database.snapshots[params[0]] = {**dict(zip(keys, params)), "created_at": "2026-08-10 12:00:00"}
        elif "FROM recommendation_observation_snapshots" in normalized:
            if "WHERE snapshot_id IN" in normalized:
                self.rows = [self.database.snapshots[snapshot_id] for snapshot_id in params if snapshot_id in self.database.snapshots]
            else:
                self.rows = list(self.database.snapshots.values())
        elif "AS event_count" in normalized:
            self.rows = [{"event_count": 0, "impressions": 0, "clicks": 0, "favorites": 0, "repeat_visits": 0}]

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)


class ObservationConnection:
    def __init__(self, database):
        self.database = database

    def cursor(self):
        return ObservationCursor(self.database)

    def close(self):
        return None

    def commit(self):
        return None


class ObservationDatabase:
    def __init__(self):
        self.statements = []
        self.snapshots = {}

    def connect(self):
        return ObservationConnection(self)


class RecommendationObservationPhase22CTests(unittest.TestCase):
    def setUp(self):
        self.database = ObservationDatabase()
        self.app = Flask(__name__)
        self.app.config.update(JWT_SECRET_KEY="phase-2-observation-test-key-at-least-32-bytes", TESTING=False, PROPAGATE_EXCEPTIONS=False)
        self.app.logger.disabled = True
        JWTManager(self.app)
        register_v1_routes(self.app, self.database.connect)
        self.client = self.app.test_client()

    def headers_for(self, identity):
        with self.app.app_context():
            token = create_access_token(identity=identity)
        return {"Authorization": f"Bearer {token}"}

    def test_zero_events_data_quality_is_healthy_and_read_only(self):
        response = self.client.get("/api/recommendation/metrics/data-quality", headers=self.headers_for("admin"))
        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        self.assertEqual(data["total_events"], 0)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["duplicate_impressions"], 0)
        self.assertTrue(any("invalid_websites" in statement for statement in self.database.statements))
        self.assertFalse(any(statement.startswith("INSERT ") or statement.startswith("UPDATE ") or statement.startswith("DELETE ") for statement in self.database.statements))

    def test_zero_events_are_not_phase_23_ready(self):
        response = self.client.get("/api/recommendation/metrics/phase-2-3-readiness", headers=self.headers_for("admin"))
        self.assertEqual(response.status_code, 200)
        data = response.get_json()["data"]
        self.assertFalse(data["ready"])
        self.assertEqual(data["events"]["impressions"]["required"], 1000)
        self.assertFalse(data["events"]["impressions"]["passed"])
        self.assertTrue(data["data_quality"]["passed"])

    def test_observation_endpoints_remain_admin_only(self):
        response = self.client.get("/api/recommendation/metrics/data-quality", headers=self.headers_for("ordinary"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_save_list_and_compare_aggregate_snapshots(self):
        headers = self.headers_for("admin")
        first = self.client.post("/api/recommendation/metrics/observation-snapshots?lookback_days=30", headers=headers)
        second = self.client.post("/api/recommendation/metrics/observation-snapshots?lookback_days=7", headers=headers)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        first_id = first.get_json()["data"]["snapshot_id"]
        second_id = second.get_json()["data"]["snapshot_id"]
        self.assertEqual(first.get_json()["data"]["algorithm_version"], "phase1-v1")
        self.assertEqual(first.get_json()["data"]["summary"]["impressions"], 0)

        listed = self.client.get("/api/recommendation/metrics/observation-snapshots", headers=headers)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.get_json()["data"]["items"]), 2)

        compared = self.client.get(
            f"/api/recommendation/metrics/observation-snapshots/compare?left_snapshot_id={first_id}&right_snapshot_id={second_id}",
            headers=headers,
        )
        self.assertEqual(compared.status_code, 200)
        self.assertTrue(compared.get_json()["data"]["same_algorithm_version"])
        self.assertEqual(compared.get_json()["data"]["delta"]["impressions"], 0)

    def test_observation_fields_are_recorded_without_touching_rank_weights(self):
        source = (BACKEND_DIR / "v1_routes.py").read_text(encoding="utf-8")
        tracker = (BACKEND_DIR / "frontend" / "src" / "utils" / "behaviorTracker.js").read_text(encoding="utf-8")
        self.assertIn('RECOMMENDATION_ALGORITHM_VERSION = "phase1-v1"', source)
        self.assertIn('"match_score_bucket"', source)
        self.assertIn('"personalization_type"', source)
        self.assertIn("match_score", tracker)
        self.assertNotIn("click +1", source)


if __name__ == "__main__":
    unittest.main()
