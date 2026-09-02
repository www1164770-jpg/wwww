import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (relativePath) =>
  readFileSync(resolve(root, relativePath), "utf8");

const home = read("src/views/Home.vue");
const api = read("src/utils/api.js");
const homeTemplate = home.slice(0, home.indexOf("<script setup>"));

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
assert.match(homeTemplate, /<h3 id="career-selection-title">选择职业<\/h3>/);
assert.match(
  homeTemplate,
  /v-if="careerAbilityTags\.length"[\s\S]*?>能力标签</,
);
assert.doesNotMatch(homeTemplate, /兴趣与目标/);
assert.doesNotMatch(homeTemplate, /v-for="tag in careerInterestTags"/);
assert.match(
  home,
  /careerInterestTags\.value = Array\.isArray\(payload\.interest_tags\)/,
);
assert.match(
  home,
  /\.career-options\s*\{[\s\S]*?overflow-y:\s*auto;[\s\S]*?scrollbar-width:\s*thin;/,
);
assert.match(
  home,
  /function canNestedScrollerConsumeWheel[\s\S]*?element\.scrollTop \+ element\.clientHeight < element\.scrollHeight/,
);
assert.match(home, /questionnaireCompleted/);
assert.match(home, /to="\/questionnaire"/);
assert.match(home, /career\.websites/);
assert.match(home, /mergeCareerSites\(code, rawSites\)/);
assert.match(api, /export function unwrapCareerRecommendationResponse/);
assert.doesNotMatch(home, /getCareerWebsites/);
assert.doesNotMatch(home, /const selectedCareer\s*=\s*["']frontend_developer/);
assert.doesNotMatch(home, /OCCUPATION_STORAGE_KEY/);

console.log("PASS questionnaire-driven career recommendations");
