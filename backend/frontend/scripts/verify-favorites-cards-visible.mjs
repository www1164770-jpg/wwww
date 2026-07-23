import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const favorites = readFileSync(resolve(root, "src/views/Favorites.vue"), "utf8");

const checks = [
  [
    "Favorites scopes card reveal registration to its rendered list",
    /ref="favoritesPanel"[\s\S]*?<SiteList\b/.test(favorites),
  ],
  [
    "Favorites registers SiteCard reveal elements with IntersectionObserver",
    /function observeFavoriteCards\([\s\S]*?querySelectorAll\("\.reveal-on-scroll"\)[\s\S]*?IntersectionObserver/.test(
      favorites,
    ),
  ],
  [
    "Favorites makes cards visible when motion is reduced or observers are unavailable",
    /reduceMotion \|\| !\("IntersectionObserver" in window\)[\s\S]*?classList\.add\("is-visible"\)/.test(
      favorites,
    ),
  ],
  [
    "Favorites registers reveals after the displayed favorite list changes",
    /watch\(\s*filteredFavorites[\s\S]*?await nextTick\(\)[\s\S]*?observeFavoriteCards\(\)/.test(
      favorites,
    ),
  ],
  [
    "Favorites disconnects its observer on unmount",
    /onBeforeUnmount\([\s\S]*?favoriteCardsObserver\?\.disconnect\(\)/.test(
      favorites,
    ),
  ],
];

const failures = checks.filter(([, passed]) => !passed).map(([name]) => name);

if (failures.length) {
  console.error("Favorites card visibility static verification failed:");
  failures.forEach((name) => console.error(`- ${name}`));
  process.exit(1);
}

console.log("Favorites card visibility static verification passed.");
