import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");

const home = read("src/views/Home.vue");
const marquee = read("src/components/home/ToolMarquee.vue");
const header = read("src/components/layout/AppHeader.vue");

const careerStart = home.indexOf('id="career-sites"');
const gridStart = home.indexOf('class="site-grid"', careerStart);
const promptStart = home.indexOf('class="ai-login-prompt"', careerStart);
const careerEnd = promptStart >= 0 ? home.indexOf("</section>", promptStart) : -1;
const reasonBindings = home.match(/:show-reason="true"/g) || [];

const checks = [
  ["Home renders an AI login prompt", promptStart >= 0],
  [
    "prompt stays inside the career recommendation section after its card grid",
    careerStart >= 0 && gridStart > careerStart && promptStart > gridStart && careerEnd > promptStart,
  ],
  ["prompt is limited to signed-out users", home.includes('<div v-if="!loggedIn" class="ai-login-prompt">')],
  ["prompt button keeps the required label", home.includes("登录并使用 AI 助手")],
  [
    "prompt uses the existing login route with a home redirect",
    /function goToAiAssistantLogin\(\)\s*\{\s*router\.push\(\{\s*path:\s*[\"']\/login[\"'],\s*query:\s*\{\s*redirect:\s*[\"']\/[\"'],?\s*\},?\s*\}\);?\s*\}/s.test(home),
  ],
  [
    "Home does not add a direct localStorage token read",
    !/localStorage\.(?:access_token|token)|localStorage\.getItem\(\s*[\"'](?:access_token|token)[\"']/.test(home),
  ],
  [
    "Home does not add an AI endpoint or assistant panel",
    !home.includes("/api/ai") && !home.includes("site-recommend") && !home.includes("AiSiteAssistantPanel"),
  ],
  ["ToolMarquee remains the unchanged name-only marquee", marquee.includes('id="tools"') && !marquee.includes("<SiteCard")],
  [
    "popular sites navigation still points to the marquee",
    header.includes('to="/#tools"') && header.includes("scrollToSection('tools')"),
  ],
  ["Home does not restore the removed hot section", !home.includes('id="hot"') && !home.includes("/#hot")],
  [
    "recommendation reasons remain enabled only for career SiteCards",
    home.includes('v-for="site in careerSites"') && reasonBindings.length === 1,
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
