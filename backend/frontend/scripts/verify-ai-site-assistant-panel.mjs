import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");
const assistantPath = resolve(root, "src/components/ai/AiSiteAssistant.vue");
const storePath = resolve(root, "src/stores/aiAssistant.js");
const assistant = existsSync(assistantPath)
  ? read("src/components/ai/AiSiteAssistant.vue")
  : "";
const store = existsSync(storePath) ? read("src/stores/aiAssistant.js") : "";
const api = read("src/utils/api.js");
const home = read("src/views/Home.vue");
const header = read("src/components/layout/AppHeader.vue");

const checks = [
  ["assistant component exists", existsSync(assistantPath)],
  ["assistant UI store exists", existsSync(storePath)],
  [
    "store only owns open and close UI state",
    /const isOpen = ref\(false\)/.test(store) &&
      /function openAssistant\(\)/.test(store) &&
      /function closeAssistant\(\)/.test(store) &&
      /function toggleAssistant\(\)/.test(store) &&
      !/localStorage|accessToken|refreshToken|Authorization|recommendSites/.test(
        store,
      ),
  ],
  [
    "API uses the existing axios client and the required endpoint",
    /export const aiAPI\s*=\s*\{[\s\S]*?recommendSites:\s*\(payload\)\s*=>\s*api\.post\(\s*["']\/ai\/site-recommend["']\s*,\s*payload\s*\)/.test(
      api,
    ),
  ],
  [
    "assistant sends only query and limit five",
    /aiAPI\.recommendSites\(\{\s*query:\s*trimmedQuery,\s*limit:\s*5,?\s*\}\)/s.test(
      assistant,
    ),
  ],
  [
    "assistant does not read tokens or manually set authorization",
    !/localStorage|getAccessToken|Authorization|Bearer\s/.test(assistant),
  ],
  [
    "Home mounts assistant only for logged-in users and reuses visitSite",
    /<AiSiteAssistant\s+v-if="loggedIn"\s+@visit="visitSite"\s*\/>/.test(home),
  ],
  [
    "signed-out users cannot see the assistant launcher",
    !assistant.includes('v-if="!loggedIn"'),
  ],
  [
    "input enforces the 500 character limit",
    /<textarea[^>]*maxlength="500"/.test(assistant),
  ],
  [
    "keyboard behavior covers Enter, Shift+Enter, IME composition and Escape",
    /@keydown="handleKeydown"/.test(assistant) &&
      /event\.isComposing|isComposing\.value/.test(assistant) &&
      /event\.key === "Enter"/.test(assistant) &&
      /event\.shiftKey/.test(assistant) &&
      /event\.key === "Escape"/.test(assistant),
  ],
  [
    "assistant handles loading, empty, general error and expired login states",
    /isLoading/.test(assistant) &&
      /empty/.test(assistant) &&
      /error/.test(assistant) &&
      /unauthorized/.test(assistant) &&
      /重新登录/.test(assistant),
  ],
  ["results hide match scores", !assistant.includes("match_score")],
  [
    "result interaction emits visit without opening windows directly",
    /emit\((["'])visit\1,\s*site\)/.test(assistant) &&
      !/window\.open|recordClick/.test(assistant),
  ],
  [
    "assistant includes accessible dialog and live status semantics",
    /role="dialog"/.test(assistant) &&
      /aria-modal="false"/.test(assistant) &&
      /aria-live="polite"/.test(assistant) &&
      /role="alert"/.test(assistant),
  ],
  [
    "AppHeader reuses the shared store without mounting a panel or calling the AI API",
    header.includes("useAiAssistantStore") &&
      header.includes("openAssistant") &&
      !header.includes("<AiSiteAssistant") &&
      !header.includes("/ai/site-recommend"),
  ],
  [
    "existing 知航AI login prompt remains",
    home.includes('class="ai-login-prompt"'),
  ],
  [
    "ToolMarquee target remains available",
    home.includes("ToolMarquee") && !home.includes('id="hot"'),
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
