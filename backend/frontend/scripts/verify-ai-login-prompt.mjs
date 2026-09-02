import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");

const home = read("src/views/Home.vue");

const careerStart = home.indexOf('id="career"');
const gridStart = home.indexOf('class="career-site-grid"', careerStart);
const promptStart = home.indexOf(
  'class="ai-login-prompt career-section-cta"',
  careerStart,
);
const careerEnd =
  promptStart >= 0 ? home.indexOf("</section>", promptStart) : -1;
const reasonBindings = home.match(/:show-reason="true"/g) || [];

const checks = [
  ["Home renders an AI assistant prompt", promptStart >= 0],
  [
    "prompt stays inside the career recommendation section after its card grid",
    careerStart >= 0 &&
      gridStart > careerStart &&
      promptStart > gridStart &&
      careerEnd > promptStart,
  ],
  [
    "prompt switches copy and action for signed-in users",
    home.includes("ai-login-prompt--authenticated") &&
      home.includes("登录并使用知航AI助手") &&
      home.includes("询问知航AI助手") &&
      home.includes('@click="handleAiAssistantEntry"'),
  ],
  [
    "signed-out prompt keeps the existing login route with a home redirect",
    /function goToAiAssistantLogin\(\)\s*\{\s*router\.push\(\{\s*path:\s*["']\/login["'],\s*query:\s*\{\s*redirect:\s*["']\/["'],?\s*\},?\s*\}\);?\s*\}/s.test(
      home,
    ),
  ],
  [
    "Home uses the shared assistant store for signed-in prompts",
    home.includes("useAiAssistantStore") &&
      /function handleAiAssistantEntry\(\)\s*\{[\s\S]*?if \(loggedIn\.value\) \{[\s\S]*?aiAssistantStore\.openAssistant\(\)/.test(
        home,
      ),
  ],
  [
    "Home does not add a direct localStorage token read or AI request",
    !/localStorage\.(?:access_token|token)|localStorage\.getItem\(\s*["'](?:access_token|token)["']|\/api\/ai|site-recommend/.test(
      home,
    ),
  ],
  [
    "Home does not restore the removed hot section",
    !home.includes('id="hot"') && !home.includes("/#hot"),
  ],
  [
    "recommendation reasons remain enabled only for career SiteCards",
    home.includes('v-for="site in visibleCareerSites"') &&
      reasonBindings.length === 1,
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
