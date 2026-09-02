import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (relativePath) =>
  readFileSync(resolve(root, relativePath), "utf8");

const home = read("src/views/Home.vue");
const api = read("src/utils/api.js");

assert.match(api, /export const careerAPI/);
assert.match(api, /getRecommendations/);
assert.match(home, /sitesByCareer\.value/);
assert.match(home, /Array\.isArray\(career\.websites\)/);
assert.match(home, /v-for="site in visibleCareerSites"/);
assert.match(home, /activeSites = computed/);
assert.match(home, /const CAREER_BATCH_SIZE = 16/);
assert.match(home, /const CAREER_SITE_POOL_MAX = 48/);
assert.match(home, /v-for="index in visibleCareerSiteCount"/);
assert.match(home, /grid-template-columns: repeat\(4, minmax\(0, 1fr\)\)/);
assert.match(home, /@media \(min-width: 768px\) and \(max-width: 1199px\)/);
assert.match(home, /@media \(max-width: 767px\)/);
assert.match(home, /const careerBatchIndex = ref\(0\)/);
assert.match(home, /function refreshCareerBatch\(event\)/);
assert.match(home, /data-testid="career-refresh-batch"/);
assert.match(home, /:show-reason="true"/);
assert.match(home, /mergeCareerSites\(/);
assert.match(home, /normalizeCareerSiteList/);
assert.match(api, /unwrapCareerRecommendationResponse/);
assert.doesNotMatch(home, /getCareerWebsites/);

console.log("PASS questionnaire-linked website recommendations");
