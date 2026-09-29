import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");
const app = read("src/App.vue");
const globalStyle = read("src/style.css");
const header = read("src/components/layout/AppHeader.vue");
const assistant = read("src/components/ai/AiSiteAssistant.vue");

const checks = [
  [
    "the app root tracks the shared assistant open state",
    /ai-assistant-open': aiAssistantStore\.isOpen/.test(app),
  ],
  [
    "one shared desktop panel width drives the layout",
    /--ai-panel-width:\s*clamp\(380px, 25vw, 420px\)/.test(globalStyle) &&
      /#app-root\.ai-assistant-open\s*\{[\s\S]*?margin-right:\s*var\(--ai-panel-width\)/.test(
        globalStyle,
      ),
  ],
  [
    "the header reserves the same right-side panel width",
    /\.app-header--home\.app-header--ai-open\s*\{[\s\S]*?right:\s*var\(--ai-panel-width\)/.test(
      header,
    ) && /\.app-header\s*\{[\s\S]*?z-index:\s*100/.test(header),
  ],
  [
    "the home header remains an unobtrusive transparent layer",
    /html\[data-personalization="on"\] \.app-header\.app-header--home\s*\{[\s\S]*?border:\s*0 !important;[\s\S]*?background:\s*rgba\(255, 255, 255, 0\.08\) !important;[\s\S]*?box-shadow:\s*none !important;[\s\S]*?backdrop-filter:\s*blur\(6px\) !important/.test(
      globalStyle,
    ),
  ],
  [
    "header content uses a three-column grid instead of viewport centering",
    /grid-template-columns:\s*minmax\(220px, 1fr\) auto minmax\(220px, 1fr\)/.test(
      header,
    ) &&
      /\.app-header--home \.nav-links\s*\{[\s\S]*?justify-self:\s*center/.test(
        header,
      ) &&
      !/\.app-header--home \.nav-links\s*\{[\s\S]*?left:\s*50%/.test(
        header,
      ),
  ],
  [
    "the panel owns an independent fixed right-side region",
    /\.ai-site-assistant__overlay\s*\{[\s\S]*?position:\s*fixed[\s\S]*?z-index:\s*300[\s\S]*?width:\s*var\(--ai-panel-width\)/.test(
      assistant,
    ),
  ],
  [
    "panel header and body have independent flex regions",
    /\.ai-site-assistant__panel\s*\{[\s\S]*?display:\s*flex[\s\S]*?flex-direction:\s*column/.test(
      assistant,
    ) &&
      /\.ai-site-assistant__body\s*\{[\s\S]*?flex:\s*1 1 auto[\s\S]*?overflow-y:\s*auto/.test(
        assistant,
      ),
  ],
  [
    "small screens retain overlay behavior without shrinking the page",
    /@media \(max-width: 1100px\)[\s\S]*?#app-root\.ai-assistant-open\s*\{[\s\S]*?margin-right:\s*0/.test(
      globalStyle,
    ) &&
      /@media \(max-width: 1100px\)[\s\S]*?\.ai-site-assistant__overlay\s*\{[\s\S]*?width:\s*100%/.test(
        assistant,
      ),
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
