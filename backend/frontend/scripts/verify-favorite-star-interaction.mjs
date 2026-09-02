import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (file) => readFileSync(resolve(root, file), "utf8");

const favoriteStar = read("src/components/site/FavoriteStarButton.vue");
const siteCard = read("src/components/site/SiteCard.vue");
const store = read("src/stores/favorites.js");
const api = read("src/utils/api.js");
const backend = read(resolve(root, "../v1_routes.py"));

const timeoutMatch = api.match(
  /FAVORITE_MUTATION_TIMEOUT_MS\s*=\s*([\d_]+)/,
);
const favoriteTimeout = Number(timeoutMatch?.[1]?.replaceAll("_", ""));
const hasReasonableMutationTimeout =
  Number.isFinite(favoriteTimeout) &&
  favoriteTimeout >= 5_000 &&
  favoriteTimeout <= 60_000;

const checks = [
  [
    "favorite root is a button",
    /<button\s+[\s\S]*type="button"/.test(favoriteStar),
  ],
  [
    "favorite click stops and prevents card actions",
    /@click\.stop\.prevent="handleToggle"/.test(favoriteStar),
  ],
  [
    "pointerdown and mousedown stop parent handling",
    /@pointerdown\.stop/.test(favoriteStar) &&
      /@mousedown\.stop/.test(favoriteStar),
  ],
  [
    "button remains enabled for URL-only sites",
    /!favoriteKey/.test(favoriteStar) &&
      !/!canUseSiteActions/.test(favoriteStar),
  ],
  [
    "favorite button accepts pointer events",
    /pointer-events:\s*auto/.test(favoriteStar) &&
      /touch-action:\s*manipulation/.test(favoriteStar),
  ],
  [
    "favorite icon cannot intercept the button",
    /\.favorite-star__icon[\s\S]*?pointer-events:\s*none/.test(favoriteStar),
  ],
  [
    "unfavorited star is hollow",
    /:fill="isFavorited \? 'currentColor' : 'none'"/.test(favoriteStar),
  ],
  ["favorited star uses current color", /currentColor/.test(favoriteStar)],
  [
    "favorite control is a background-free icon action",
    /\.favorite-star\s*\{[\s\S]*?top:\s*18px[\s\S]*?right:\s*18px[\s\S]*?padding:\s*4px[\s\S]*?border:\s*0[\s\S]*?background:\s*transparent[\s\S]*?box-shadow:\s*none/.test(
      favoriteStar,
    ),
  ],
  [
    "favorite colors use adaptive theme variables",
    /color:\s*var\(--favorite-muted-color\)/.test(favoriteStar) &&
      /\.favorite-star\.is-favorite\s*\{[\s\S]*?color:\s*var\(--favorite-color\)/.test(
        favoriteStar,
      ),
  ],
  [
    "hover feedback only strengthens and scales the icon",
    /\.favorite-star:hover:not\(:disabled\)\s+\.favorite-star__icon\s*\{[\s\S]*?transform:\s*scale\(1\.1\)/.test(
      favoriteStar,
    ) &&
      !/\.favorite-star:hover:not\(:disabled\)\s*\{[^}]*transform:/.test(
        favoriteStar,
      ),
  ],
  [
    "hover does not disable the button",
    !favoriteStar.includes("is-spinning") && !favoriteStar.includes("Loader"),
  ],
  [
    "pending is per favorite key",
    /favoriteKey/.test(favoriteStar) && /getFavoriteKey/.test(store),
  ],
  ["numeric ids have stable id keys", /return `id:\$\{siteId\}`/.test(store)],
  [
    "URL-only sites have stable URL keys",
    /return urlKey \? `url:\$\{urlKey\}`/.test(store),
  ],
  [
    "URL-only sites are valid optimistic favorites",
    /!favoriteKey \|\| !name \|\| !url/.test(store) &&
      /id: siteId \|\| favoriteKey/.test(store),
  ],
  [
    "pending state is cleared on add",
    /favoriteAPI\.addFavorite\(site, note\)[\s\S]*?finally \{\s*endPending\(favoriteKey\)/.test(
      store,
    ),
  ],
  [
    "pending state is cleared on remove",
    /favoriteAPI\.removeFavorite\(site\)[\s\S]*?finally \{\s*endPending\(favoriteKey\)/.test(
      store,
    ),
  ],
  [
    "API uses the id endpoint for numeric ids",
    /target\.siteId[\s\S]*?api\.post\([\s\S]*?`\/sites\/\$\{target\.siteId\}\/favorite`[\s\S]*?timeout:\s*FAVORITE_MUTATION_TIMEOUT_MS/.test(
      api,
    ) && hasReasonableMutationTimeout,
  ],
  [
    "API uses the reference endpoint for URL-only sites",
      /const url = target\.siteId[\s\S]*?"\/favorites"/.test(api) &&
      /const payload = target\.siteId[\s\S]*?\{ url: target\.url, note \}/.test(api) &&
      /api\.post\(url, payload[\s\S]*?config\.timeout/.test(api) &&
      /api\.delete\(url, [\s\S]*?data: payload[\s\S]*?config\.timeout/.test(api) &&
      hasReasonableMutationTimeout,
  ],
  [
    "backend resolves URL references",
    /def resolve_favorite_site_id/.test(backend) &&
      /LOWER\(url\)/.test(backend),
  ],
  [
    "backend exposes URL add and remove routes",
    /@app\.route\("\/api\/favorites", methods=\["POST"\]\)/.test(backend) &&
      /methods=\["DELETE"\]/.test(backend),
  ],
  [
    "card uses article and shared favorite control",
    /<article[\s\S]*?<FavoriteStarButton/.test(siteCard),
  ],
  [
    "card has no anchor wrapping the favorite control",
    !/<a\b[\s\S]*?<FavoriteStarButton/.test(siteCard),
  ],
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
  console.error(`\n${failed} favorite star interaction check(s) failed.`);
  process.exit(1);
}
