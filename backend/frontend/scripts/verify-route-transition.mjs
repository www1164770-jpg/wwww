import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");
const app = read("src/App.vue");
const router = read("src/router/index.js");
const index = read("index.html");
const home = read("src/views/Home.vue");
const search = read("src/views/SearchResults.vue");

const checks = [
  [
    "Header and AI assistant live in the persistent app layout",
    /<AppHeader v-if="showAppHeader"\s*\/>/.test(app) &&
      /<AiSiteAssistant @visit="visitAiRecommendation"\s*\/>/.test(app) &&
      !home.includes("<AppHeader") &&
      !home.includes("<AiSiteAssistant"),
  ],
  [
    "route content uses a keyed cross-fade transition",
    /<Transition name="route-page">[\s\S]*?<component :is="Component" :key="route\.fullPath"/.test(
      app,
    ) &&
      /\.route-page-enter-active\s*\{[\s\S]*?opacity 400ms cubic-bezier\(0\.22, 1, 0\.36, 1\)[\s\S]*?transform 400ms cubic-bezier\(0\.22, 1, 0\.36, 1\)/.test(
        app,
      ) &&
      /\.route-page-leave-active\s*\{[\s\S]*?position:\s*absolute[\s\S]*?opacity 220ms ease/.test(
        app,
      ),
  ],
  [
    "page roots reserve viewport height and scrollbar space",
    /\.app-route-content\s*\{[\s\S]*?min-height:\s*100vh/.test(app) &&
      /scrollbar-gutter:\s*stable/.test(app),
  ],
  [
    "ordinary navigation resets without a competing smooth scroll",
    /return\s*\{\s*top:\s*0,\s*behavior:\s*"auto"/.test(router),
  ],
  [
    "the shared ink background is preloaded once",
    /<link rel="preload" as="image" href="\/src\/assets\/home-ink-landscape\.png"\s*\/>/.test(
      index,
    ),
  ],
  [
    "next-page views no longer mount their own header",
    !search.includes("<AppHeader") && !search.includes("import AppHeader"),
  ],
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
