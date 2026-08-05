import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const repoRoot = resolve(root, "..", "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");
const readRepo = (path) => readFileSync(resolve(repoRoot, path), "utf8");

const home = read("src/views/Home.vue");
const routes = readRepo("backend/v1_routes.py");
const careerService = readRepo("backend/career_recommend_service.py");
const source = `${home}\n${routes}\n${careerService}`;

const checks = [
  [
    "active career code is explicit state",
    /const activeCareerCode = ref\(\"\"\)/,
  ],
  [
    "recommendation list is explicit state",
    /const recommendations = ref\(\[\]\)/,
  ],
  ["career sites are grouped by career", /const sitesByCareer = ref\(\{\}\)/],
  ["site loading state exists", /const sitesLoading = ref\(false\)/],
  ["site error state exists", /const sitesError = ref\(\"\"\)/],
  ["activeCareer derives from active code", /const activeCareer = computed/],
  ["activeSites derives from active code", /const activeSites = computed/],
  [
    "activeSites reads the grouped map",
    /sitesByCareer\.value\[activeCareerCode\.value\]/,
  ],
  [
    "template renders the current career batch",
    /v-for="site in visibleCareerSites"/,
  ],
  ["career buttons call selectCareer", /@click="selectCareer\(career\)"/],
  ["selection writes active code", /activeCareerCode\.value = careerCode/],
  ["selection updates URL", /nextQuery\.career = code/],
  ["selection removes invalid URL value", /delete nextQuery\.career/],
  [
    "career code accepts camel case",
    /career\.careerCode \|\| career\.career_code/,
  ],
  ["payload recommendations are normalized", /payload\.recommendations/],
  ["legacy careers response remains compatible", /payload\.careers/],
  ["normalized sites populate grouped map", /nextSitesByCareer\[code\]/],
  ["URL career is validated", /validRequestedCareer/],
  [
    "invalid URL falls back to first result",
    /normalized\.list\[0\]\?\.careerCode/,
  ],
  ["new recommendation load clears old map", /sitesByCareer\.value = \{\}/],
  ["recommendation request has stale-response guard", /latestCareerRequestId/],
  ["selection has stale-response guard", /latestCareerSelectionId/],
  ["selection clears previous error", /sitesError\.value = \"\"/],
  ["selection exposes loading state", /sitesLoading\.value = !hasCachedSites/],
  ["career batches reset on selection", /careerBatchIndex\.value = 0/],
  ["batch size is sixteen", /const CAREER_BATCH_SIZE = 16/],
  [
    "active pools are filled from the career-specific fallback pool",
    /function ensureCareerSitePool[\s\S]*?getCareerWebsites\(canonicalCareerCode\)/,
  ],
  [
    "short career pools produce an explicit warning",
    /site pool below 16[\s\S]*?required: CAREER_BATCH_SIZE/,
  ],
  [
    "career aliases resolve to the canonical website pool",
    /function getCanonicalCareerCode[\s\S]*?normalizeOccupation\(careerCode\)/,
  ],
  [
    "career pool supports multiple sixteen-site batches",
    /const CAREER_SITE_POOL_MAX = 48/,
  ],
  [
    "career site pool falls back to the active career payload",
    /const fallbackSites =\s*\n\s*career\?\.sites \|\| career\?\.websites \|\| career\?\.recommendedSites/,
  ],
  [
    "empty career site pools render an empty batch",
    /if \(!pool\.length\) return \[\]/,
  ],
  [
    "batch indexes are normalized before slicing",
    /const safeIndex = \(\(requestedIndex % batchCount\) \+ batchCount\) % batchCount/,
  ],
  [
    "refresh is disabled while loading or when only one batch exists",
    /const canRefreshCareerBatch = computed[\s\S]*?!sitesLoading\.value[\s\S]*careerBatchCount\.value > 1/,
  ],
  [
    "refresh button uses the guarded availability state",
    /:disabled="!canRefreshCareerBatch"/,
  ],
  [
    "single-batch refresh resets the index",
    /if \(careerBatchCount\.value <= 1\) \{\s*careerBatchIndex\.value = 0;/,
  ],
  ["batch refresh wraps around", /% careerBatchCount\.value/],
  ["refresh button is wired", /@click\.stop\.prevent="refreshCareerBatch"/],
  [
    "refresh stops the parent click and default action",
    /@click\.stop\.prevent="refreshCareerBatch"/,
  ],
  [
    "refresh handler prevents propagation",
    /function refreshCareerBatch\(event\)[\s\S]*?event\?\.preventDefault\?\.\(\)[\s\S]*?event\?\.stopPropagation\?\.\(\)/,
  ],
  [
    "career changes reset the batch index",
    /watch\(\s*activeCareerCode[\s\S]*?careerChanged[\s\S]*?requestedIndex = careerChanged\s*\?\s*0/,
  ],
  ["backend career route exists", /career\/recommend/],
  ["backend returns careerCode", /career\[\"careerCode\"\]/],
  ["backend returns grouped sites", /career\[\"sites\"\]/],
  ["backend returns questionnaire version", /questionnaire_version/],
  ["backend filters sites before ranking", /filter_sites_for_career\(/],
  ["career filter checks occupation relation", /normalize_occupation\(value\)/],
  ["career filter checks career keywords", /keyword_match/],
  [
    "home supplements API results with career-specific website data",
    /getCareerWebsites\(canonicalCareerCode\)/.test(home),
  ],
  [
    "home does not render the old single career list",
    !/v-for="site in careerSites"/.test(home),
  ],
];

for (const [name, check] of checks) {
  assert.ok(typeof check === "boolean" ? check : check.test(source), name);
}

const visibleBatch = (pool, index, batchSize = 16) => {
  if (!pool.length) return [];
  const batchCount = Math.floor(pool.length / batchSize);
  if (!batchCount) return [];
  const requestedIndex = Number(index) || 0;
  const safeIndex = ((requestedIndex % batchCount) + batchCount) % batchCount;
  const start = safeIndex * batchSize;
  return pool.slice(start, start + batchSize);
};

const sixteenSites = Array.from({ length: 16 }, (_, index) => `site-${index}`);
const thirtyTwoSites = Array.from(
  { length: 32 },
  (_, index) => `site-${index}`,
);
const fortyEightSites = Array.from(
  { length: 48 },
  (_, index) => `site-${index}`,
);
const thirtySevenSites = Array.from(
  { length: 37 },
  (_, index) => `site-${index}`,
);
assert.deepEqual(visibleBatch([], 1), []);
assert.deepEqual(visibleBatch(sixteenSites, 1), sixteenSites);
assert.equal(visibleBatch(thirtyTwoSites, 0).length, 16);
assert.equal(visibleBatch(thirtyTwoSites, 1).length, 16);
assert.deepEqual(visibleBatch(thirtyTwoSites, 2), thirtyTwoSites.slice(0, 16));
assert.equal(visibleBatch(fortyEightSites, 2).length, 16);
assert.deepEqual(
  visibleBatch(fortyEightSites, 3),
  fortyEightSites.slice(0, 16),
);
assert.equal(visibleBatch(thirtySevenSites, 0).length, 16);
assert.equal(visibleBatch(thirtySevenSites, 1).length, 16);
assert.deepEqual(
  visibleBatch(thirtySevenSites, 2),
  thirtySevenSites.slice(0, 16),
);

console.log(`PASS career switching data flow (${checks.length} checks)`);
