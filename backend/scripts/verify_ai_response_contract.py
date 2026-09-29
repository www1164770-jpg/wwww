"""Capture actual Flask response envelopes for the frontend contract replay."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "backend"), str(ROOT)]
from test_ai_site_recommend_v1 import AiSiteRecommendRouteTests, AI_INVALID_QUERY_CASES


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/data/stage1-ai-response-contract.json")
    args = parser.parse_args()
    case = AiSiteRecommendRouteTests()
    case.setUp()
    responses = []
    labels = ["missing_query", "null_query", "numeric_query", "blank_query", "too_short", "too_long"]
    def capture(label, response, expected_state):
        responses.append({"case": label, "status": response.status_code, "body": response.get_json(), "expected_state": expected_state})
    for label, (payload, message) in zip(labels, AI_INVALID_QUERY_CASES):
        response = case.client.post("/api/ai/site-recommend", json=payload, headers=case.headers())
        case.assert_error_contract(response, 400, message)
        capture(label, response, "error")
    with patch("v1_routes.recommend_sites_for_query", side_effect=RuntimeError("private-fixture-secret")), case.assertLogs(case.app.logger, level="ERROR"):
        response = case.client.post("/api/ai/site-recommend", json={"query": "Python 调试"}, headers=case.headers())
    case.assert_error_contract(response, 500, "推荐服务暂时不可用")
    capture("internal_failure", response, "error")
    for label, query, state in [("normal_match", "Python 调试", "success"), ("no_match", "量子烹饪机器人", "empty")]:
        response = case.client.post("/api/ai/site-recommend", json={"query": query}, headers=case.headers())
        case.assertEqual(response.status_code, 200)
        case.assertIs(response.get_json()["success"], True)
        capture(label, response, state)
    for label, headers, code in [("missing_login", {}, 401), ("invalid_token", {"Authorization": "Bearer not-a-token"}, 422)]:
        response = case.client.post("/api/ai/site-recommend", json={"query": "Python 调试"}, headers=headers)
        case.assertEqual(response.status_code, code)
        capture(label, response, "unauthorized")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"source": "real Flask routes with isolated fake catalog", "cases": responses}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(responses)} real response fixtures; no user data or tokens written")


if __name__ == "__main__":
    main()
