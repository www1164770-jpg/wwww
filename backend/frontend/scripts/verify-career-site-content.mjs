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
assert.match(api, /function isUsableSiteSummary\(/);
assert.match(api, /!\/\^\(\?:https\?:\\\/\\\/\|www\\\.\)\/i\.test/);

assert.doesNotMatch(home, /getCareerWebsites|careerWebsiteMap/);
assert.match(home, /const apiSiteList = normalizeCareerSiteList\(apiSites\)/);
assert.match(home, /return ensureCareerSitePool\(careerCode, apiSiteList\)/);

assert.match(api, /const values = \[[\s\S]*?site\.summary[\s\S]*?site\.description/);
assert.match(api, /!RETIRED_GENERIC_SITE_DESCRIPTIONS\.has\(text\)/);

console.log("PASS career site quantity and summary adaptation");
