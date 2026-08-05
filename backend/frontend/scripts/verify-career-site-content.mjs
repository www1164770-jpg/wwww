import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (relativePath) =>
  readFileSync(resolve(root, relativePath), "utf8");

const hero = read("src/components/home/HeroSearch.vue");
const home = read("src/views/Home.vue");
const siteCard = read("src/components/site/SiteCard.vue");
const api = read("src/utils/api.js");
const careerBlockStart = siteCard.indexOf('<template v-if="isCareerVariant">');
const careerBlockEnd = siteCard.indexOf("</template>", careerBlockStart);
const careerBlock = siteCard.slice(careerBlockStart, careerBlockEnd);

assert.match(hero, /根据你的职业，推荐最适合的工具/);
assert.doesNotMatch(hero, /根据你的职业，推荐最适合的\s*AI工具/);
assert.doesNotMatch(hero, /根据你的职业，推荐最适合的\s*AI\s*工具/);
assert.match(siteCard, /data-testid="career-site-summary"/);
assert.match(siteCard, /<SiteLogo/);
assert.ok(careerBlock);
assert.doesNotMatch(careerBlock, /访问/);
assert.doesNotMatch(careerBlock, /career-card-visit/);
assert.doesNotMatch(careerBlock, /site-card-tags/);
assert.doesNotMatch(careerBlock, /ExternalLink/);
assert.match(siteCard, /-webkit-line-clamp: 2/);
assert.match(home, /const CAREER_SITE_POOL_MAX = 48/);
assert.match(home, /const CAREER_BATCH_SIZE = 16/);
assert.match(home, /v-for="index in 16"/);
assert.match(home, /visibleCareerSites/);
assert.match(home, /refreshCareerBatch/);
assert.match(home, /normalizeCareerSiteList/);
assert.match(api, /export function normalizeCareerSite\(/);
assert.match(api, /export function generateFallbackSummary\(/);
assert.match(api, /function isUsableSiteSummary\(/);
assert.match(api, /!\/\^\(\?:https\?:\\\/\\\/\|www\\\.\)\/i\.test/);
assert.match(api, /site\.slogan/);
assert.doesNotMatch(api, /generateFallbackSummary[\s\S]{0,700}site\.url/);

const { careerWebsiteMap } = await import("../src/data/careerWebsites.js");

const careerCodes = [
  "frontend_developer",
  "backend_developer",
  "data_analyst",
  "ai_app_developer",
  "llm_engineer",
  "product_manager",
  "ui_ux_designer",
  "student",
  "operations",
  "other",
  "teacher",
  "creator",
  "technical_operations",
];
const careerSiteSets = careerCodes.map((code) => {
  const sites = careerWebsiteMap[code] || [];
  assert.ok(
    sites.length >= 32 && sites.length <= 48,
    `${code} source site pool must contain 32 to 48 sites`,
  );
  const urls = sites.map((site) => site.url);
  assert.equal(
    new Set(urls).size,
    urls.length,
    `${code} source site pool contains duplicates`,
  );
  for (const site of sites) {
    assert.ok(
      site.name && site.url && site.shortDescription,
      `${code} site cards need name, URL and summary`,
    );
  }
  return new Set(urls);
});

for (let index = 1; index < careerSiteSets.length; index += 1) {
  assert.notDeepEqual(
    [...careerSiteSets[0]],
    [...careerSiteSets[index]],
    `${careerCodes[0]} and ${careerCodes[index]} reuse the same sites`,
  );
}

assert.match(
  api,
  /const values = \[[\s\S]*?site\.summary[\s\S]*?site\.description[\s\S]*?site\.slogan/,
);
assert.match(
  api,
  /const categorySummary = CAREER_CATEGORY_SUMMARY_FALLBACKS\[category\]/,
);
assert.match(api, /const tags = normalizeStringArray\(site\.tags\)/);
assert.match(api, /提供适合当前职业方向的学习与实践资源/);

console.log("PASS career site quantity and summary adaptation");
