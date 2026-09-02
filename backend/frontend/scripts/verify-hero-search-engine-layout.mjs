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
const suggestionsCss =
  searchBar.match(/\.search-suggestions\s*\{([^}]*)\}/)?.[1] || "";

const checks = [
  [
    "search shell has the wider desktop width",
    /width:\s*min\(820px,\s*calc\(100vw - 40px\)\)/.test(searchBar),
  ],
  [
    "search input expands without its own frame",
    /\.search-input\s*\{[\s\S]*?flex:\s*1[\s\S]*?border:\s*0[\s\S]*?background:\s*transparent[\s\S]*?box-shadow:\s*none/.test(
      searchBar,
    ),
  ],
  [
    "search input keeps focus styling on the shell",
    /\.search-input:focus\s*\{[\s\S]*?box-shadow:\s*none !important/.test(
      searchBar,
    ) && /\.search-bar:focus-within/.test(searchBar),
  ],
  [
    "search shell owns the adaptive glass surface",
    /\.search-bar\s*\{[\s\S]*?background:\s*var\(--app-surface\)/.test(
      searchBar,
    ) &&
      /\.search-bar\s*\{[\s\S]*?border:\s*1px solid var\(--app-card-border\)/.test(
        searchBar,
      ),
  ],
  [
    "custom search scope trigger has enough desktop width and adaptive glass",
    /\.engine-picker\s*\{[\s\S]*?flex:\s*0 0 170px[\s\S]*?height:\s*56px/.test(
      searchBar,
    ) &&
      /\.engine-picker__trigger\s*\{[\s\S]*?background:\s*var\(--app-card-bg\)[\s\S]*?backdrop-filter:\s*blur\(16px\)/.test(
        searchBar,
      ),
  ],
  [
    "search button has a fixed desktop size",
    /\.search-button\s*\{[\s\S]*?flex:\s*0 0 62px[\s\S]*?width:\s*62px[\s\S]*?height:\s*62px/.test(
      searchBar,
    ),
  ],
  [
    "suggestion menu is an adaptive strong overlay",
    /position:\s*absolute/.test(suggestionsCss) &&
      /top:\s*calc\(100% \+ 10px\)/.test(suggestionsCss) &&
      /z-index:\s*1000/.test(suggestionsCss) &&
      /background:\s*var\(--app-surface-strong\)/.test(suggestionsCss),
  ],
  [
    "hero receives suggestion open state",
    /engineMenuOpen[\s\S]*?@engine-menu-change/.test(heroSearch),
  ],
  [
    "hero keeps its visible content structurally rendered",
    /<div class="hero-copy">[\s\S]*?<HeroStrokeTitle(?:\s[^>]*)?>[\s\S]*?<SearchBar[\s\S]*?hero-stats/.test(
      heroSearch,
    ),
  ],
  [
    "hero keeps the reveal class while adding only the menu state",
    /<section\s+class="hero-search reveal-on-scroll"\s+:class="\{\s*'engine-menu-open': engineMenuOpen\s*\}"/.test(
      heroSearch,
    ),
  ],
  [
    "hero suggestion state starts closed",
    /const engineMenuOpen\s*=\s*ref\(false\)/.test(heroSearch),
  ],
  [
    "hero has a direct visible fallback when the observer has not run",
    /opacity:\s*1/.test(heroVisibleFallbackCss) &&
      /transform:\s*none/.test(heroVisibleFallbackCss),
  ],
  [
    "hero has no suggestion spacer in any state",
    !/274px/.test(heroSearch) &&
      !/\.hero-search__search-area\.engine-menu-open/.test(heroSearch),
  ],
  [
    "hero open state changes stacking only",
    /z-index:\s*50/.test(heroOpenCss) &&
      !/(padding|margin)-(top|bottom)|\bheight\s*:|\bmin-height\s*:/.test(
        heroOpenCss,
      ),
  ],
  [
    "hero permits the overlay to escape vertically",
    /overflow:\s*visible/.test(heroRootCss) &&
      /z-index:\s*50/.test(heroOpenCss),
  ],
  [
    "mobile search remains one row and suggestion menu stays in viewport",
    /@media \(max-width: 560px\)[\s\S]*?\.search-bar\s*\{[\s\S]*?width:\s*min\(820px, calc\(100vw - 32px\)\)[\s\S]*?\.search-suggestions\s*\{[\s\S]*?width:\s*calc\(100vw - 32px\)/.test(
      searchBar,
    ),
  ],
  [
    "tool marquee keeps its behavior free of a raised z-index",
    !/\.tool-marquee\s*\{[\s\S]*?z-index\s*:/.test(toolMarquee),
  ],
  [
    "external engine selection is available without replacing internal search",
    /const SEARCH_ENGINES = Object\.freeze/.test(searchBar) &&
      /const searchEngine = ref\("internal"\)/.test(searchBar) &&
      /window\.open\(target, "_blank", "noopener,noreferrer"\)/.test(searchBar),
  ],
  [
    "engine picker uses an accessible custom listbox instead of native select",
    !/<select\b|<option\b/.test(searchBar) &&
      /aria-haspopup="listbox"/.test(searchBar) &&
      /role="listbox"/.test(searchBar) &&
      /role="option"/.test(searchBar),
  ],
  [
    "engine picker supports keyboard navigation and outside closing",
    /handleEngineTriggerKeydown/.test(searchBar) &&
      /event\.key === "ArrowDown"/.test(searchBar) &&
      /event\.key === "ArrowUp"/.test(searchBar) &&
      /event\.key === "Escape"/.test(searchBar) &&
      /closeEngineMenu\(\)/.test(searchBar),
  ],
  [
    "engine menu glass panel fits long labels and mobile viewports",
    /\.engine-menu\s*\{[\s\S]*?min-width:\s*220px[\s\S]*?max-width:\s*min\(260px, 80vw\)[\s\S]*?background:\s*var\(--app-panel-bg\)[\s\S]*?backdrop-filter:\s*blur\(var\(--app-blur\)\)/.test(
      searchBar,
    ) &&
      /@media \(max-width: 560px\)[\s\S]*?\.engine-menu\s*\{[\s\S]*?calc\(100vw - 32px\)/.test(
        searchBar,
      ),
  ],
  [
    "outside-click closing remains",
    /function handleDocumentPointerDown\([\s\S]*?closeSuggestions\(\)/.test(
      searchBar,
    ),
  ],
  [
    "Escape closing remains",
    /event\.key === "Escape"[\s\S]*?closeSuggestions\(\)/.test(searchBar),
  ],
  [
    "internal search submit behavior remains available",
    /function submit\(\)[\s\S]*?submitValue\(keyword\.value\)/.test(
      searchBar,
    ) &&
      /recentSearches\.value = searchStore\.addRecentSearch\(query\)[\s\S]*?emit\("search", query\)[\s\S]*?router\.push\(\{ path: "\/search"/.test(
        searchBar,
      ),
  ],
];

const failures = checks.filter(([, passed]) => !passed).map(([name]) => name);

if (failures.length) {
  console.error("Hero internal search layout static verification failed:");
  failures.forEach((name) => console.error(`- ${name}`));
  process.exit(1);
}

if (!packageJson.includes('"test:hero-search-engine-layout"')) {
  console.error(
    "package.json does not register test:hero-search-engine-layout",
  );
  process.exit(1);
}

console.log("Hero internal search layout static verification passed.");
