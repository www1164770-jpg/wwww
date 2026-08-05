import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const frontendDir = path.resolve(scriptDir, "..");
const store = fs.readFileSync(
  path.join(frontendDir, "src/stores/favorites.js"),
  "utf8",
);
const favoriteError = fs.readFileSync(
  path.join(frontendDir, "src/utils/favoriteError.js"),
  "utf8",
);
const favoritesView = fs.readFileSync(
  path.join(frontendDir, "src/views/Favorites.vue"),
  "utf8",
);
const api = fs.readFileSync(path.join(frontendDir, "src/utils/api.js"), "utf8");

assert.match(store, /zhihangyu:favorites:/);
assert.match(store, /FAVORITE_CACHE_TTL_MS = 5 \* 60_000/);
assert.match(store, /FAVORITE_CACHE_VERSION = 1/);
assert.match(store, /getFavoriteCacheKey/);
assert.match(store, /cacheRestored/);
assert.match(store, /status\.value = "restoring"/);
assert.match(store, /cached\.userId/);
assert.match(store, /loadPromiseUserId/);
assert.match(store, /background/);
assert.match(favoriteError, /DATABASE_UNAVAILABLE/);
assert.match(favoriteError, /AUTH_REQUIRED/);
assert.match(favoriteError, /TIMEOUT/);
assert.match(favoriteError, /NETWORK_ERROR/);
assert.match(store, /localStorage\.setItem/);
assert.match(store, /localStorage\.removeItem/);
assert.match(store, /window\.addEventListener\("storage"/);
assert.match(store, /onScopeDispose/);
assert.match(store, /favoriteId/);
assert.match(store, /seenFavoriteKeys/);
assert.match(store, /seenUrls/);
assert.match(store, /normalizeFavorite\(site\)/);
assert.match(favoritesView, /useFavoritesStore/);
assert.match(favoritesView, /restoreFavoriteCache/);
assert.match(favoritesView, /favoriteStore\.loadFavorites/);
assert.match(favoritesView, /favoriteStore\.hasSnapshot/);
assert.match(favoritesView, /favoriteStore\.isRefreshing/);
assert.match(favoritesView, /background: restored/);
assert.doesNotMatch(favoritesView, /favoritePendingIds|favoriteIds/);
assert.match(store, /persistFavoriteCache: persistCache/);
assert.match(store, /hasFavorites: computed/);
assert.doesNotMatch(favoritesView, /categoryAPI\.getCategories/);
assert.match(
  api,
  /getFavorites: \(config = \{\}\) => api\.get\("\/favorites", config\)/,
);

console.log("favorites cache checks passed");
