import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");

const header = read("src/components/layout/AppHeader.vue");
const home = read("src/views/Home.vue");
const marquee = read("src/components/home/ToolMarquee.vue");

const navStart = header.indexOf('<nav class="nav-links"');
const navEnd = navStart >= 0 ? header.indexOf("</nav>", navStart) : -1;
const entryStart = header.indexOf('class="nav-ai-login-entry"');
const sharedNav = header.slice(navStart, navEnd);

const checks = [
  ["AppHeader includes the AI assistant entry", header.includes("AI 助手") && entryStart >= 0],
  [
    "entry is limited to signed-out users through the existing login state",
    header.includes('v-if="!loggedIn"') && entryStart > navStart && entryStart < navEnd,
  ],
  [
    "entry uses the existing login route with a home redirect",
    /function goToAiAssistantLogin\(\)\s*\{\s*router\.push\(\{\s*path:\s*[\"']\/login[\"'],\s*query:\s*\{\s*redirect:\s*[\"']\/[\"'],?\s*\},?\s*\}\);?\s*\}/s.test(header),
  ],
  ["entry is a normal button rather than an AI page anchor", /<button[\s\S]*?nav-ai-login-entry[\s\S]*?@click="goToAiAssistantLogin"/.test(sharedNav)],
  [
    "the shared responsive navigation keeps the entry available on small screens",
    header.includes("@media (max-width: 900px)") && header.match(/class="nav-links"/g)?.length === 1,
  ],
  ["the existing general login button remains", header.includes('class="login-link" to="/login"')],
  ["AI entry does not use an AI scroll target", !header.includes("scrollToSection('ai')") && !header.includes("/#ai")],
  ["Home does not add an AI section", !home.includes('id="ai"')],
  [
    "no AI endpoint or assistant panel was added",
    !header.includes("/api/ai") &&
      !header.includes("site-recommend") &&
      !header.includes("AiSiteAssistantPanel") &&
      !home.includes("/api/ai"),
  ],
  [
    "AppHeader does not add a direct localStorage token read",
    !/localStorage\.(?:access_token|token)|localStorage\.getItem\(\s*[\"'](?:access_token|token)[\"']/.test(header),
  ],
  [
    "popular sites navigation still points to the marquee",
    header.includes('to="/#tools"') && header.includes("scrollToSection('tools')") && marquee.includes('id="tools"'),
  ],
  ["the old hot section remains absent", !header.includes("/#hot") && !home.includes('id="hot"')],
  ["the homepage AI login prompt remains", home.includes('class="ai-login-prompt"')],
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
