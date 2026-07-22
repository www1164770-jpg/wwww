import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");
const header = read("src/components/layout/AppHeader.vue");
const home = read("src/views/Home.vue");
const assistant = read("src/components/ai/AiSiteAssistant.vue");
const store = read("src/stores/aiAssistant.js");
const marquee = read("src/components/home/ToolMarquee.vue");

const assistantMounts = home.match(/<AiSiteAssistant\b/g) || [];
const checks = [
  ["Header imports the shared AI assistant store", header.includes("useAiAssistantStore")],
  ["Header creates one store reference", /const aiAssistantStore = useAiAssistantStore\(\)/.test(header)],
  [
    "Header AI entry stays available for both authentication states",
    /<button[\s\S]*?class="nav-ai-login-entry"[\s\S]*?@click="handleAiAssistantEntry"/.test(header) &&
      !/v-if="!loggedIn"[\s\S]*?class="nav-ai-login-entry"/.test(header),
  ],
  [
    "Header opens the shared panel for logged-in users",
    /function handleAiAssistantEntry\(\)\s*\{[\s\S]*?if \(loggedIn\.value\) \{[\s\S]*?aiAssistantStore\.openAssistant\(\)/.test(header),
  ],
  [
    "Header keeps the existing login redirect for signed-out users",
    /function goToAiAssistantLogin\(\)\s*\{\s*router\.push\(\{\s*path:\s*["']\/login["'],\s*query:\s*\{\s*redirect:\s*["']\/["'],?\s*\},?\s*\}\);?\s*\}/s.test(header),
  ],
  ["Header does not mount an AI panel or call an AI API", !header.includes("<AiSiteAssistant") && !header.includes("site-recommend")],
  ["Header does not use an AI anchor", !header.includes("/#ai") && !header.includes("scrollToSection('ai')")],
  ["Home imports the shared AI assistant store", home.includes("useAiAssistantStore")],
  ["Home creates one shared store reference", /const aiAssistantStore = useAiAssistantStore\(\)/.test(home)],
  [
    "Home uses one authentication-aware AI entry handler",
    /function handleAiAssistantEntry\(\)\s*\{[\s\S]*?if \(loggedIn\.value\) \{[\s\S]*?aiAssistantStore\.openAssistant\(\)/.test(home),
  ],
  ["Home keeps the signed-out AI prompt and login label", home.includes("登录并使用 AI 助手")],
  ["Home adds the signed-in AI prompt and entry label", home.includes("询问 AI 助手")],
  ["Home prompt uses the shared AI entry handler", /class="ai-login-prompt[^"]*"[\s\S]*?@click="handleAiAssistantEntry"/.test(home)],
  ["Home mounts exactly one assistant instance", assistantMounts.length === 1 && /<AiSiteAssistant\s+v-if="loggedIn"\s+@visit="visitSite"\s*\/>/.test(home)],
  [
    "Home closes the panel when login state becomes invalid",
    /watch\(loggedIn,\s*\(isLoggedIn\)\s*=>\s*\{\s*if \(!isLoggedIn\) \{\s*aiAssistantStore\.closeAssistant\(\)/s.test(home),
  ],
  ["The floating launcher remains in the existing panel", assistant.includes("AI 帮我找网站") && assistant.includes("toggleAssistant")],
  ["The shared store remains UI-only with open and close methods", /function openAssistant\(\)/.test(store) && /function closeAssistant\(\)/.test(store)],
  ["No direct token reads or AI requests were added to entry points", !/localStorage|Authorization|site-recommend|\/api\/ai/.test(`${header}\n${home}`)],
  ["Popular sites navigation still targets the marquee", header.includes('to="/#tools"') && marquee.includes('id="tools"')],
  ["The removed hot section remains absent", !home.includes('id="hot"') && !header.includes("/#hot")],
  ["Career SiteCards keep recommendation reasons enabled", home.includes(':show-reason="true"')],
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
