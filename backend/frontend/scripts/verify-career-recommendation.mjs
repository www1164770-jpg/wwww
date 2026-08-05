import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (relativePath) =>
  readFileSync(resolve(root, relativePath), "utf8");

const home = read("src/views/Home.vue");
const api = read("src/utils/api.js");

assert.match(api, /export const careerAPI\s*=\s*\{/);
assert.match(api, /api\.get\("\/career\/recommend"/);
assert.match(home, /careerAPI\.getRecommendations/);
assert.match(home, /v-for="career in careerRecommendations"/);
assert.match(home, /const activeCareerCode = ref\(""\)/);
assert.match(home, /const activeSites = computed/);
assert.match(home, /@click="selectCareer\(career\)"/);
assert.match(home, /career\.match_score/);
assert.match(home, /career\.reason/);
assert.match(home, /careerAbilityTags/);
assert.match(home, /careerInterestTags/);
assert.match(home, /questionnaireCompleted/);
assert.match(home, /to="\/questionnaire"/);
assert.match(home, /career\.websites/);
assert.match(home, /getCareerWebsites\(canonicalCareerCode\)/);
assert.match(home, /mergeCareerSites\(code, rawSites\)/);
assert.doesNotMatch(home, /const selectedCareer\s*=\s*["']frontend_developer/);
assert.doesNotMatch(home, /OCCUPATION_STORAGE_KEY/);

console.log("PASS questionnaire-driven career recommendations");
