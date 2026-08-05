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
const heroRootCss = heroSearch.match(/\.hero-search\s*\{([^}]*)\}/)?.[1] || "";
const heroVisibleFallbackCss =
  heroSearch.match(/\.hero-search\.reveal-on-scroll\s*\{([^}]*)\}/)?.[1] || "";
const heroOpenCss =
  heroSearch.match(/\.hero-search\.engine-menu-open\s*\{([^}]*)\}/)?.[1] || "";
const enginePickerCss =
  searchBar.match(/\.engine-picker\s*\{([^}]*)\}/)?.[1] || "";
const engineMenuCss =
  searchBar.match(/\.engine-picker__menu\s*\{([^}]*)\}/)?.[1] || "";

const checks = [
  ["search shell has the wider desktop width", /width:\s*min\(820px,\s*calc\(100vw - 40px\)\)/.test(searchBar)],
  ["search input expands without its own frame", /\.search-input\s*\{[\s\S]*?flex:\s*1[\s\S]*?border:\s*0[\s\S]*?background:\s*transparent[\s\S]*?box-shadow:\s*none/.test(searchBar)],
  ["search input keeps focus styling on the shell", /\.search-input:focus\s*\{[\s\S]*?box-shadow:\s*none !important/.test(searchBar) && /\.search-bar:focus-within/.test(searchBar)],
  ["search shell owns the unified subtle outline", /\.search-bar\s*\{[\s\S]*?background:\s*rgba\(255, 255, 255, 0\.86\)/.test(searchBar) && /\.search-bar\s*\{[\s\S]*?border:\s*1px solid rgba\(255, 107, 87, 0\.34\)/.test(searchBar)],
  ["engine trigger has a stable desktop width", /\.engine-picker__button\s*\{[\s\S]*?flex:\s*0 0 145px[\s\S]*?height:\s*56px/.test(searchBar)],
  ["search button has a fixed desktop size", /\.search-button\s*\{[\s\S]*?flex:\s*0 0 64px[\s\S]*?width:\s*64px[\s\S]*?height:\s*62px/.test(searchBar)],
  ["engine menu is an opaque absolute overlay above its picker", /position:\s*relative/.test(enginePickerCss) && /position:\s*absolute/.test(engineMenuCss) && /top:\s*calc\(100% \+ 10px\)/.test(engineMenuCss) && /z-index:\s*1000/.test(engineMenuCss) && /background:\s*#ffffff/.test(engineMenuCss) && /width:\s*230px/.test(engineMenuCss) && /max-height:\s*260px/.test(engineMenuCss) && /overflow-y:\s*auto/.test(engineMenuCss)],
  ["hero receives the engine menu open state", /engineMenuOpen[\s\S]*?@engine-menu-change/.test(heroSearch)],
  ["hero keeps its visible content structurally rendered", /<div class="hero-copy">[\s\S]*?<h1(?:\s[^>]*)?>[\s\S]*?<SearchBar[\s\S]*?hero-stats/.test(heroSearch)],
  ["hero keeps the reveal class while adding only the menu state", /<section\s+class="hero-search reveal-on-scroll"\s+:class="\{\s*'engine-menu-open': engineMenuOpen\s*\}"/.test(heroSearch)],
  ["hero menu state starts closed", /const engineMenuOpen\s*=\s*ref\(false\)/.test(heroSearch)],
  ["hero has a direct visible fallback when the observer has not run", /opacity:\s*1/.test(heroVisibleFallbackCss) && /transform:\s*none/.test(heroVisibleFallbackCss)],
  ["hero has no menu spacer in any state", !/274px/.test(heroSearch) && !/\.hero-search__search-area\.engine-menu-open/.test(heroSearch)],
  ["hero menu state changes stacking only", /z-index:\s*50/.test(heroOpenCss) && !/(padding|margin)-(top|bottom)|\bheight\s*:|\bmin-height\s*:/.test(heroOpenCss)],
  ["hero permits the overlay to escape vertically and wins its sibling stack", /overflow:\s*visible/.test(heroRootCss) && /z-index:\s*50/.test(heroOpenCss)],
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
