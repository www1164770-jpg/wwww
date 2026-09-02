import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");
const page = read("src/views/admin/RecommendationMetrics.vue");
const api = read("src/utils/api.js");
const router = read("src/router/index.js");
const layout = read("src/components/admin/AdminLayout.vue");

assert.match(router, /path: "recommendation-metrics"/);
assert.match(router, /requiresAdmin: true/);
assert.match(layout, /\/admin\/recommendation-metrics/);
assert.match(api, /export const recommendationMetricsAPI/);
for (const method of ["getSummary", "getBatches", "getWebsites", "getProfileOverlap", "getDataQuality", "getPhase23Readiness", "createObservationSnapshot", "getObservationSnapshots", "compareObservationSnapshots"]) {
  assert.match(api, new RegExp(`${method}:`));
}
assert.match(page, /最近 7 天/);
assert.match(page, /最近 30 天/);
assert.match(page, /最近 90 天/);
assert.match(page, /value="all"/);
assert.match(page, /group_by: "day"/);
assert.match(page, /loadWebsites/);
assert.match(page, /loadOverlap/);
assert.match(page, /样本不足/);
assert.match(page, /暂无真实行为数据/);
assert.match(page, /personalized_ratio/);
assert.match(page, /batch_repeat_rate/);
assert.match(page, /exclude_test_users/);
assert.match(page, /match_score_bucket/);
assert.match(page, /personalization_type/);
assert.match(page, /数据质量/);
assert.match(page, /Phase 2\.3 数据准备度/);
assert.match(page, /保存本次观察快照/);
assert.match(page, /snapshotHistory/);
assert.match(page, /compareObservationSnapshots/);

console.log("PASS recommendation metrics dashboard checks");
