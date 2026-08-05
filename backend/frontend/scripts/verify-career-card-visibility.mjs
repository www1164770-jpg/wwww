import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const home = readFileSync(resolve(root, "src/views/Home.vue"), "utf8");
const siteCard = readFileSync(
  resolve(root, "src/components/site/SiteCard.vue"),
  "utf8",
);

const careerStart = home.indexOf('data-testid="career-recommendations"');
const careerGridStart = home.indexOf(
  'data-testid="career-site-batch"',
  careerStart,
);
const careerGridEnd = home.indexOf('class="ai-login-prompt"', careerGridStart);
const careerGrid = home.slice(careerGridStart, careerGridEnd);
const siteCardStyleStart = siteCard.indexOf("<style scoped>");
const siteCardStyle = siteCard.slice(siteCardStyleStart);

const checks = [
  ["career website rendering uses a normal grid", /class="career-site-grid"/],
  [
    "career grid does not keep TransitionGroup overlays",
    !/TransitionGroup/.test(careerGrid),
  ],
  ["career keys include the active career", /activeCareerCode/],
  ["career keys include the active batch", /activeCareerBatchIndex/],
  ["career keys normalize website URLs", /normalizeUrl\(site\.url\)/],
  [
    "career cards do not use scroll reveal opacity",
    /!isCategoryVariant[^\n]*!isCareerVariant/,
  ],
  [
    "career card wrapper is explicitly visible",
    /\.career-site-grid[\s\S]*?opacity: 1/,
  ],
  [
    "career card wrapper keeps visibility enabled",
    /\.career-site-grid[\s\S]*?visibility: visible/,
  ],
  [
    "career card wrapper has no hidden transform",
    /\.career-site-grid[\s\S]*?transform: none/,
  ],
  [
    "career card itself remains an article",
    /<article\s+class="site-card website-card"/,
  ],
  [
    "career card click emits the website visit",
    /else if \(isCareerVariant\.value\) openSite\(\)/,
  ],
  ["career card links stop propagation", /@click\.stop\.prevent="openSite"/],
  [
    "career grid has no absolute leave positioning",
    !/career-sites-leave-active|position:\s*absolute/.test(careerGrid),
  ],
];

for (const [name, check] of checks) {
  assert.ok(
    typeof check === "boolean" ? check : check.test(`${home}\n${siteCard}`),
    name,
  );
}

assert.match(
  siteCardStyle,
  /\.website-card--career\s*\{[\s\S]*?display:\s*flex/,
);
assert.match(
  siteCardStyle,
  /\.website-card--career\s*\{[\s\S]*?min-height:\s*180px/,
);

console.log(
  `PASS career card visibility and click area (${checks.length + 2} checks)`,
);
