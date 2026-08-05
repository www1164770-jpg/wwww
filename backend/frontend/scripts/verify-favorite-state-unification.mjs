import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptsDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptsDir, "..");
const read = (relativePath) =>
  fs.readFileSync(path.join(frontendDir, relativePath), "utf8");

const store = read("src/stores/favorites.js");
const favoriteStar = read("src/components/site/FavoriteStarButton.vue");
const siteList = read("src/components/site/SiteList.vue");
const views = [
  "src/views/Home.vue",
  "src/views/SearchResults.vue",
  "src/views/CategoryDetail.vue",
  "src/views/ProfileView.vue",
  "src/views/SiteDetail.vue",
  "src/views/Favorites.vue",
].map(read);

assert.match(store, /getFavoriteKey,\n\s+loadFavorites/);
assert.match(store, /async function toggleFavorite\(site/);
assert.match(store, /persistCache\(userId\)/);
assert.match(favoriteStar, /favoritesStore\.getFavoriteKey/);
assert.match(favoriteStar, /favoritesStore\.toggleFavorite\(normalizedSite\.value\)/);
assert.match(favoriteStar, /favoritesStore\.isFavorite\(normalizedSite\.value\)/);
assert.match(favoriteStar, /favoritesStore\.loadFavorites/);
assert.doesNotMatch(favoriteStar, /source|route\.name|route\.path/);
assert.doesNotMatch(siteList, /favoriteIds|favoritePendingIds|@favorite/);

for (const view of views) {
  assert.doesNotMatch(view, /favoriteAPI/);
  assert.doesNotMatch(view, /favoritePendingIds|favoriteSiteIds|favoriteStateLoaded/);
}

const siteDetail = read("src/views/SiteDetail.vue");
assert.match(siteDetail, /favoritesStore\.toggleFavorite\(site\.value\)/);
assert.match(siteDetail, /isSiteFavorited/);

console.log("favorite state unification checks passed");
