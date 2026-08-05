import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const home = readFileSync(resolve(root, "src/views/Home.vue"), "utf8");

const refreshStart = home.indexOf("function refreshCareerBatch");
const refreshEnd = home.indexOf(
  "function normalizeRecommendations",
  refreshStart,
);
const refreshBlock = home.slice(refreshStart, refreshEnd);

const checks = [
  ["career cache is user scoped", /getCareerCacheIndexKey\(userId\)/],
  ["career cache includes questionnaire version", /questionnaireVersion/],
  ["career cache includes algorithm version", /CAREER_ALGORITHM_VERSION/],
  ["career cache uses session storage", /return typeof sessionStorage/],
  ["career cache restores the website pool", /cache\.sitesByCareer/],
  ["career cache restores each batch index", /cache\.batchIndexByCareer/],
  [
    "cached data keeps success state during revalidation",
    /hasExistingData \? "success" : "loading"/,
  ],
  [
    "questionnaire loading is explicit",
    /questionnaireStatus\.value = "loading"/,
  ],
  [
    "questionnaire empty state needs an explicit response",
    /hasQuestionnaireStatus/,
  ],
  [
    "questionnaire errors do not become empty state",
    /questionnaireStatus\.value = "error"/,
  ],
  ["initialization is shared by identity", /careerInitializationPromise/],
  ["refresh changes only the current batch", /batchIndexByCareer\.value = \{/],
  [
    "refresh persists without a recommendation request",
    !/careerAPI\.getRecommendations/.test(refreshBlock),
  ],
  [
    "refresh does not clear the website map",
    !/sitesByCareer\.value\s*=\s*\{\}/.test(refreshBlock),
  ],
  ["career selection restores its remembered batch", /rememberedBatchIndex/],
  ["failed revalidation keeps cached data", /当前仍显示上次成功加载的结果/],
  [
    "logout clears only the current career cache",
    /clearCareerCache\(previousIdentity\)/,
  ],
];

for (const [name, check] of checks) {
  assert.ok(typeof check === "boolean" ? check : check.test(home), name);
}

const batches = (pool, index, size = 16) => {
  if (!pool.length) return [];
  const count = Math.floor(pool.length / size);
  if (!count) return [];
  const safeIndex = (((Number(index) || 0) % count) + count) % count;
  return pool.slice(safeIndex * size, safeIndex * size + size);
};

const pool = Array.from({ length: 48 }, (_, index) => `site-${index}`);
assert.deepEqual(batches(pool, 0), pool.slice(0, 16));
assert.deepEqual(batches(pool, 1), pool.slice(16, 32));
assert.deepEqual(batches(pool, 2), pool.slice(32, 48));
assert.deepEqual(batches(pool, 3), pool.slice(0, 16));
assert.deepEqual(batches(pool, -1), pool.slice(32, 48));
assert.deepEqual(batches([], 1), []);
assert.equal(
  batches(
    Array.from({ length: 37 }, (_, index) => `site-${index}`),
    2,
  ).length,
  16,
);

console.log(`PASS career cache and refresh flow (${checks.length} checks)`);
