import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const read = (path) => readFileSync(resolve(root, path), "utf8");

function collectSourceFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) return collectSourceFiles(path);
    return /\.(?:vue|js)$/.test(entry.name) ? [path] : [];
  });
}

const header = read("src/components/layout/AppHeader.vue");
const home = read("src/views/Home.vue");
const favorites = read("src/views/Favorites.vue");
const router = read("src/router/index.js");
const globalStyles = read("src/style.css");
const sourceFiles = collectSourceFiles(resolve(root, "src"));
const toolsIdCount = sourceFiles.reduce(
  (count, path) =>
    count +
    (readFileSync(path, "utf8").match(/id=["']tools["']/g) || []).length,
  0,
);

const checks = [
  [
    "Header exposes one favorites navigation entry",
    (header.match(/data-testid="favorites-navigation-link"/g) || []).length ===
      1 &&
      /<RouterLink[\s\S]*?class="nav-item nav-favorites"[\s\S]*?to="\/favorites"[\s\S]*?data-testid="favorites-navigation-link"[\s\S]*?<\/RouterLink>/.test(
        header,
      ),
  ],
  [
    "favorites entry keeps the existing AI entry as a separate navigation item",
    header.includes('data-testid="ai-assistant-entry"') &&
      header.includes('data-testid="favorites-navigation-link"'),
  ],
  [
    "favorites entry uses the shared Star icon",
    header.includes('import { Star } from "lucide-vue-next"') &&
      /<Star[\s\S]*?class="favorite-star-icon"/.test(header),
  ],
  [
    "old tools navigation entry is removed from the header",
    !header.includes('data-testid="tools-navigation-link"') &&
      !header.includes('class="nav-item nav-tools"') &&
      !header.includes("handleToolsNavigation"),
  ],
  [
    "favorites route requires authentication",
    /path: "\/favorites"[\s\S]*?name: "Favorites"[\s\S]*?meta: \{ requiresAuth: true \}/.test(
      router,
    ),
  ],
  [
    "favorites page uses the shared favorite store and site list",
    favorites.includes("useFavoritesStore") &&
      favorites.includes("favoriteStore.loadFavorites") &&
      /<SiteList[\s\S]*?filteredFavorites/.test(favorites),
  ],
  [
    "homepage keeps one stable tools section",
    home.includes('id="tools"') &&
      home.includes("home-anchor-section") &&
      toolsIdCount === 1,
  ],
  [
    "router resolves hash navigation after the destination renders",
    router.includes("scrollBehavior(to, from, savedPosition)") &&
      router.includes("if (to.hash)") &&
      router.includes("el: to.hash") &&
      router.includes("setTimeout"),
  ],
  [
    "hash navigation respects the fixed header offset",
    router.includes("const HEADER_OFFSET = 88") &&
      router.includes("top: HEADER_OFFSET") &&
      globalStyles.includes(".home-anchor-section") &&
      globalStyles.includes("scroll-margin-top: 96px"),
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
