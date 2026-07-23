import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const searchBar = readFileSync(
  resolve(root, "src/components/common/SearchBar.vue"),
  "utf8",
);
const heroSearch = readFileSync(
  resolve(root, "src/components/home/HeroSearch.vue"),
  "utf8",
);
const toolMarquee = readFileSync(
  resolve(root, "src/components/home/ToolMarquee.vue"),
  "utf8",
);
const packageJson = readFileSync(resolve(root, "package.json"), "utf8");

const checks = [
  ["search shell has the wider desktop width", /width:\s*min\(820px,\s*calc\(100vw - 40px\)\)/.test(searchBar)],
  ["search input expands without its own frame", /\.search-input\s*\{[\s\S]*?flex:\s*1[\s\S]*?border:\s*0[\s\S]*?background:\s*transparent[\s\S]*?box-shadow:\s*none/.test(searchBar)],
  ["search input keeps focus styling on the shell", /\.search-input:focus\s*\{[\s\S]*?box-shadow:\s*none !important/.test(searchBar) && /\.search-bar:focus-within/.test(searchBar)],
  ["search shell owns the unified subtle outline", /\.search-bar\s*\{[\s\S]*?background:\s*rgba\(255, 255, 255, 0\.86\)/.test(searchBar) && /\.search-bar\s*\{[\s\S]*?border:\s*1px solid rgba\(255, 107, 87, 0\.34\)/.test(searchBar)],
  ["engine trigger has a stable desktop width", /\.engine-picker__button\s*\{[\s\S]*?flex:\s*0 0 145px[\s\S]*?height:\s*56px/.test(searchBar)],
  ["search button has a fixed desktop size", /\.search-button\s*\{[\s\S]*?flex:\s*0 0 64px[\s\S]*?width:\s*64px[\s\S]*?height:\s*62px/.test(searchBar)],
  ["engine menu is above regular content and scrollable", /\.engine-picker__menu\s*\{[\s\S]*?z-index:\s*300[\s\S]*?width:\s*230px[\s\S]*?max-height:\s*260px[\s\S]*?overflow-y:\s*auto/.test(searchBar)],
  ["hero receives the engine menu open state", /engineMenuOpen[\s\S]*?@engine-menu-change/.test(heroSearch)],
  ["hero reserves vertical menu space when open", /\.hero-search__search-area\.engine-menu-open\s*\{[\s\S]*?padding-bottom:\s*274px/.test(heroSearch)],
  ["hero permits the menu to escape vertically and wins its sibling stack", /\.hero-search\s*\{[\s\S]*?overflow:\s*visible/.test(heroSearch) && /\.hero-search\.engine-menu-open\s*\{[\s\S]*?z-index:\s*[12]/.test(heroSearch)],
  ["mobile search remains one row and menu stays in viewport", /@media \(max-width: 420px\)[\s\S]*?\.search-bar\s*\{[\s\S]*?display:\s*flex[\s\S]*?\.engine-picker__menu\s*\{[\s\S]*?width:\s*min\(230px, calc\(100vw - 32px\)\)/.test(searchBar)],
  ["tool marquee keeps its behavior free of a raised z-index", !/\.tool-marquee\s*\{[\s\S]*?z-index\s*:/.test(toolMarquee)],
  ["engine selection behavior remains", /function selectEngine\([\s\S]*?engineOpen\.value = false/.test(searchBar)],
  ["outside-click closing remains", /function handleDocumentClick\([\s\S]*?closeEngineMenu\(\)/.test(searchBar)],
  ["Escape closing remains", /function handleDocumentKeydown\([\s\S]*?event\.key === "Escape"[\s\S]*?closeEngineMenu\(\)/.test(searchBar)],
  ["search submit behavior remains", /function submit\([\s\S]*?router\.push[\s\S]*?window\.open/.test(searchBar)],
];

const failures = checks.filter(([, passed]) => !passed).map(([name]) => name);

if (failures.length) {
  console.error("Hero search engine layout static verification failed:");
  failures.forEach((name) => console.error(`- ${name}`));
  process.exit(1);
}

if (!packageJson.includes('"test:hero-search-engine-layout"')) {
  console.error("package.json does not register test:hero-search-engine-layout");
  process.exit(1);
}

console.log("Hero search engine layout static verification passed.");
