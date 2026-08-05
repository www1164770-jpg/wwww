import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (file) => readFileSync(resolve(root, file), "utf8");

const siteCard = read("src/components/site/SiteCard.vue");
const favoriteStar = read("src/components/site/FavoriteStarButton.vue");
const normalizer = read("src/utils/normalizeSite.js");
const recommend = read("src/components/home/RecommendSection.vue");
const category = read("src/components/home/CategorySection.vue");
const categoryDetail = read("src/views/CategoryDetail.vue");
const home = read("src/views/Home.vue");
const aiAssistant = read("src/components/ai/AiSiteAssistant.vue");
const favoriteStack = read("src/components/home/FavoriteStack.vue");
const toolCard = read("src/components/home/ToolCard.vue");
const store = read("src/stores/favorites.js");
const api = read("src/utils/api.js");
const packageJson = JSON.parse(read("package.json"));

const checks = [
  [
    "SiteCard uses the shared favorite component",
    /<FavoriteStarButton[\s\S]*?:site="site"/.test(siteCard),
  ],
  [
    "The career card uses the shared SiteCard",
    /variant="career"[\s\S]*?@visit="visitSite"/.test(home),
  ],
  [
    "The favorite control uses a filled Star icon",
    /import \{ Star \}/.test(favoriteStar) &&
      /:fill="isFavorited \? 'currentColor' : 'none'"/.test(favoriteStar) &&
      !/Bookmark/.test(favoriteStar),
  ],
  [
    "Pending state is local and does not replace the Star with a spinner",
    /favoritesStore\.isPending\(normalizedSite\.value\)/.test(favoriteStar) &&
      /is-pending/.test(favoriteStar) &&
      !/LoaderCircle|is-spinning/.test(favoriteStar),
  ],
  [
    "Favorite clicks stop propagation and prevent link defaults",
    /@click\.stop\.prevent="handleToggle"/.test(favoriteStar),
  ],
  [
    "Favorite state has an accessible pressed label",
    /:aria-pressed="isFavorited"/.test(favoriteStar) &&
      /:aria-label="ariaLabel"/.test(favoriteStar) &&
      /:title="ariaLabel"/.test(favoriteStar),
  ],
  [
    "Every card keeps the Star actionable with an id or URL",
      !/<button\s+v-if=/.test(favoriteStar) &&
      /:disabled="disabled \|\| !favoriteKey"/.test(favoriteStar) &&
      /favoritesStore\.getFavoriteKey/.test(favoriteStar) &&
      /url:/.test(store),
  ],
  [
    "The recommendation card avoids anchor/button nesting",
    /<article[\s\S]*?<a[\s\S]*?<\/a>[\s\S]*?<FavoriteStarButton/.test(
      recommend,
    ) && !/<a\b[^>]*>[\s\S]*?<button\b/.test(recommend),
  ],
  [
    "The category section renders SiteCard favorites",
    /<SiteCard[\s\S]*?variant="category"/.test(category),
  ],
  [
    "The category detail page renders SiteCard favorites",
    /<SiteCard[\s\S]*?variant="category"[\s\S]*?@select="handleWebsiteClick"/.test(
      categoryDetail,
    ),
  ],
  [
    "AI recommendation result cards use the shared favorite component",
    /class="ai-site-assistant__result"[\s\S]*?<FavoriteStarButton\s+:site="site"/.test(
      aiAssistant,
    ),
  ],
  [
    "The common-tools card keeps its link and favorite button as siblings",
    /<article[\s\S]*?class="compact-tool-card"[\s\S]*?<a[\s\S]*?<\/a>[\s\S]*?<FavoriteStarButton/.test(
      favoriteStack,
    ) &&
      !/<a\b[^>]*>[\s\S]*?<FavoriteStarButton[\s\S]*?<\/a>/.test(favoriteStack),
  ],
  [
    "The standalone tool card uses the shared favorite component",
    /<FavoriteStarButton\s+:site="site"/.test(toolCard) &&
      !/@click="\$emit\('toggle-favorite'/.test(toolCard),
  ],
  [
    "The store exposes shared favorite state helpers",
    /function isFavorite\(/.test(store) &&
      /function isPending\(/.test(store) &&
      /async function toggleFavorite\(/.test(store),
  ],
  [
    "Add and remove pending state is always cleared",
    /function endPending\(favoriteKey\)/.test(store) &&
      /favoriteAPI\.addFavorite\(site, note\)[\s\S]*?finally \{\s*endPending\(favoriteKey\)/.test(
        store,
      ) &&
      /favoriteAPI\.removeFavorite\(site\)[\s\S]*?finally \{\s*endPending\(favoriteKey\)/.test(
        store,
      ),
  ],
  [
    "Duplicate add and missing remove are idempotent",
    /status === 409/.test(store) && /status === 404/.test(store),
  ],
  [
    "The recommendation section accepts database-backed sites",
    /sites: \{ type: Array/.test(recommend) &&
      /featuredRecommendationSites/.test(home),
  ],
  [
    "The recommendation mapping can use URL-only catalog sites",
    /hasDatabaseId/.test(home) && /url:/.test(store),
  ],
  [
    "Favorite normalization accepts alternate website link fields",
    /site\.link/.test(api) && /link/.test(normalizer),
  ],
  [
    "The shared normalizer keeps one stable site id and display fields",
    /siteId/.test(normalizer) &&
      /logoUrl/.test(normalizer) &&
      /categoryName/.test(normalizer),
  ],
  [
    "The favorite verifier remains an npm script",
    packageJson.scripts?.["test:site-favorites"] ===
      "node scripts/verify-site-favorites.mjs",
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
  console.error(`\n${failed} site favorite verification check(s) failed.`);
  process.exit(1);
}
