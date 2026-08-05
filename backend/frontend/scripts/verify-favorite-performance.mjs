import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const read = (relativePath) =>
  fs.readFileSync(path.join(root, relativePath), "utf8");

const store = read("src/stores/favorites.js");
const favoriteStar = read("src/components/site/FavoriteStarButton.vue");
const siteDetail = read("src/views/SiteDetail.vue");
const api = read("src/utils/api.js");
const backend = read("../v1_routes.py");
const toggleBlock =
  store.match(/async function toggleFavorite[\s\S]*?function handleFavoriteStateChanged/)?.[0] ||
  "";

const handleToggle = favoriteStar.match(
  /function handleToggle\(\)[\s\S]*?\n\}/,
)?.[0] || "";

const checks = [
  ["click handler is synchronous", /^function handleToggle\(\)/.test(handleToggle)],
  [
    "UI state is read immediately after scheduling sync",
    /toggleFavorite\(normalizedSite\.value\)[\s\S]*?isFavorite\(normalizedSite\.value\)/.test(
      handleToggle,
    ),
  ],
  ["same-site desired state queue exists", /desiredStateByKey/.test(store)],
  ["same-site sync promise queue exists", /syncPromiseByKey/.test(store)],
  [
    "pending does not disable the star",
    /:disabled="disabled \|\| !favoriteKey"/.test(favoriteStar),
  ],
  ["slow sync errors are handled asynchronously", /syncPromise\.catch/.test(handleToggle)],
  [
    "favorite mutation timeout is at least eight seconds",
    /FAVORITE_MUTATION_TIMEOUT_MS\s*=\s*(\d+)/.test(api) &&
      Number(api.match(/FAVORITE_MUTATION_TIMEOUT_MS\s*=\s*(\d+)/)[1]) >= 8000,
  ],
  ["site detail does not disable its favorite action while syncing", !/:disabled="favoriteLoading"/.test(siteDetail)],
  ["backend exposes favorite timing stages", /favorite_%s_timing/.test(backend) && /commit_ms/.test(backend)],
  ["favorite operations do not reload the list", !/loadFavorites/.test(toggleBlock)],
];

let failed = 0;
for (const [name, passed] of checks) {
  if (passed) console.log(`PASS ${name}`);
  else {
    failed += 1;
    console.error(`FAIL ${name}`);
  }
}

if (failed) {
  console.error(`\n${failed} favorite performance check(s) failed.`);
  process.exitCode = 1;
} else {
  console.log("favorite performance checks passed");
}
