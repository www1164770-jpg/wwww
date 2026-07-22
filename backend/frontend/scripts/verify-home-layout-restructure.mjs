import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (relativePath) => readFileSync(resolve(root, relativePath), "utf8");
const header = read("src/components/layout/AppHeader.vue");
const hero = read("src/components/home/HeroSearch.vue");
const home = read("src/views/Home.vue");
const categories = read("src/components/home/CategorySection.vue");

const checks = [
  ["Header navigation has the required six-item order", /to="\/"[\s\S]*?\u9996\u9875[\s\S]*?to="\/#tools"[\s\S]*?\u70ed\u95e8\u7f51\u7ad9[\s\S]*?to="\/#career"[\s\S]*?\u804c\u4e1a\u63a8\u8350[\s\S]*?to="\/#categories"[\s\S]*?\u70ed\u95e8\u5206\u7c7b[\s\S]*?to="\/#recommend-tools"[\s\S]*?\u5e38\u7528\u5de5\u5177[\s\S]*?nav-ai-login-entry/.test(header)],
  ["Header removes legacy navigation items", !/\u5206\u7c7b\u5bfc\u822a|AI\u5de5\u5177|\u6700\u65b0\u6536\u5f55/.test(header)],
  ["Popular sites still target the marquee", /to="\/#tools"[\s\S]*?\u70ed\u95e8\u7f51\u7ad9/.test(header)],
  ["Home orders marquee, career, categories, and recommendations", home.indexOf("<ToolMarquee") < home.indexOf("<CareerRecommend") && home.indexOf("<CareerRecommend") < home.indexOf("<CategorySection") && home.indexOf("<CategorySection") < home.indexOf("<RecommendSection")],
  ["Home gives common tools an independent anchor", /id="recommend-tools"[\s\S]*?<RecommendSection/.test(home)],
  ["Home no longer mounts latest sites", !/<LatestSitesSection\b/.test(home)],
  ["Latest sites component remains available", existsSync(resolve(root, "src/components/home/LatestSitesSection.vue"))],
  ["AI prompt remains after career site cards", home.indexOf("class=\"ai-login-prompt\"") > home.indexOf("<SiteCard")],
  ["Home retains one authenticated assistant", (home.match(/<AiSiteAssistant\b/g) || []).length === 1 && /<AiSiteAssistant\s+v-if="loggedIn"/.test(home)],
  ["Category section removes the split copy column", !/category-copy|category-menu|\u6309\u573a\u666f\u6d4f\u89c8 AI \u5de5\u5177/.test(categories)],
  ["Category section uses a full-width heading and grid", /class="category-heading\b/.test(categories) && /grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\)/.test(categories)],
  ["Category grid becomes one column on mobile", /@media \(max-width: 720px\)[\s\S]*?grid-template-columns:\s*minmax\(0, 1fr\)/.test(categories)],
  ["Category cards have no fixed 330px minimum height", !/min-height:\s*330px/.test(categories)],
  ["Hero is substantially shorter than the previous 660px maximum", /min-height:\s*clamp\(380px, 46vh, 480px\)/.test(hero)],
  ["Hero uses compact mobile sizing", /@media \(max-width: 640px\)[\s\S]*?min-height:\s*auto[\s\S]*?padding:\s*72px 16px 36px/.test(hero)],
  ["Hero retains the search bar", /hero-search__bar/.test(hero)],
  ["Home keeps recommendation reasons and removes the old hot anchor", /:show-reason="true"/.test(home) && !/id="hot"/.test(home)],
];

let failed = false;
for (const [name, passed] of checks) {
  if (passed) console.log(`PASS ${name}`);
  else {
    failed = true;
    console.error(`FAIL ${name}`);
  }
}

if (failed) process.exitCode = 1;
