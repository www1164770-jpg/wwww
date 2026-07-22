import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");

const home = read("src/views/Home.vue");
const card = read("src/components/site/SiteCard.vue");
const marquee = read("src/components/home/ToolMarquee.vue");
const header = read("src/components/layout/AppHeader.vue");

const checks = [
  [
    "career recommendation continues to render SiteCard with reasons enabled",
    home.includes('v-for="site in careerSites"') && home.includes(':show-reason="true"'),
  ],
  [
    "SiteCard keeps recommendation reasons opt-in by default",
    card.includes("showReason: { type: Boolean, default: false }") &&
      card.includes('v-if="showReason"'),
  ],
  [
    "recommendation reason prefers the API reason and has a non-empty fallback",
    [
      "props.site.reason",
      "props.site.recommend_reason",
      "props.site.recommendation_reason",
      "props.site.match_reason",
      "props.site.summary",
      "props.site.description",
      "该网站的功能与你当前选择的职业需求较为匹配。",
    ].every((snippet, index, snippets) =>
      card.indexOf(snippet) >= 0 &&
      (index === 0 || card.indexOf(snippets[index - 1]) < card.indexOf(snippet)),
    ),
  ],
  [
    "recommendation reason text is limited to two lines",
    /\.site-card__reason-text\s*\{[\s\S]*?-webkit-line-clamp:\s*2;/.test(card),
  ],
  [
    "ToolMarquee remains a name-only marquee rather than a card list",
    !marquee.includes("<SiteCard") && marquee.includes('id="tools"'),
  ],
  [
    "popular sites navigation still points to the marquee and hot section stays removed",
    header.includes('to="/#tools"') &&
      header.includes("scrollToSection('tools')") &&
      !home.includes('id="hot"'),
  ],
];

let failed = false;
for (const [name, passed] of checks) {
  if (passed) {
    console.log(`PASS ${name}`);
  } else {
    failed = true;
    console.error(`FAIL ${name}`);
  }
}

if (failed) process.exitCode = 1;
