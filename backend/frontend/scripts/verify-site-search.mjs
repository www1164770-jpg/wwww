import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (file) => readFileSync(resolve(root, file), "utf8");
const searchBar = read("src/components/common/SearchBar.vue");
const results = read("src/views/SearchResults.vue");
const store = read("src/stores/search.js");
const api = read("src/utils/api.js");
const card = read("src/components/site/SiteCard.vue");
const siteList = read("src/components/site/SiteList.vue");
const filterDropdown = read("src/components/search/SearchFilterDropdown.vue");
const packageJson = read("package.json");

const checks = [
  [
    "search form submits",
    /<form[^>]*@submit\.prevent="submit"/.test(searchBar),
  ],
  [
    "button has a dynamic engine search label",
    /:aria-label="`使用\$\{currentEngine\.label\}搜索`"/.test(searchBar),
  ],
  [
    "engine menu height is bounded to four visible rows",
    /\.engine-menu\s*\{[\s\S]*?height: auto;[\s\S]*?min-height: 0;[\s\S]*?max-height: 204px;/.test(
      searchBar,
    ) &&
      /\.engine-menu\s*\{[\s\S]*?width: 100%;/.test(searchBar),
  ],
  [
    "all requested external engines are configured",
    [
      "baidu.com/s?wd=",
      "google.com/search?q=",
      "bing.com/search?q=",
      "github.com/search?q=",
      "stackoverflow.com/search?q=",
      "zhihu.com/search?q=",
      "juejin.cn/search?query=",
      "search.bilibili.com/all?keyword=",
    ].every((url) => searchBar.includes(url)),
  ],
  [
    "external keywords are encoded and opened safely",
    /encodeURIComponent\(query\)/.test(searchBar) &&
      /window\.open\(target, "_blank", "noopener,noreferrer"\)/.test(searchBar),
  ],
  [
    "external searches bypass internal history and search events",
    /if \(searchEngine\.value !== "internal"\) \{[\s\S]*?window\.open[\s\S]*?return;[\s\S]*?searchStore\.addRecentSearch\(query\)[\s\S]*?emit\("search", query\)/.test(
      searchBar,
    ),
  ],
  ["300ms debounce", /SEARCH_DEBOUNCE_MS\s*=\s*300/.test(searchBar)],
  ["short Latin input is skipped", /value\.length >= 2/.test(searchBar)],
  ["single Chinese input is allowed", /3400-\\u9fff/.test(searchBar)],
  ["suggestions use AbortController", /new AbortController/.test(searchBar)],
  [
    "stale suggestion response is guarded",
    /sequence !== requestSequence/.test(searchBar),
  ],
  [
    "suggestions are capped at eight",
    /MAX_SUGGESTIONS\s*=\s*8/.test(searchBar),
  ],
  [
    "keyboard arrows are supported",
    /ArrowDown/.test(searchBar) && /ArrowUp/.test(searchBar),
  ],
  ["Escape closes suggestions", /event\.key === "Escape"/.test(searchBar)],
  ["Tab closes suggestions", /event\.key === "Tab"/.test(searchBar)],
  [
    "highlighting is segmented",
    /highlightSegments/.test(searchBar) &&
      /<mark v-if="segment\.matched">/.test(searchBar),
  ],
  [
    "recent searches are scoped",
    /zhihangyu:recent-searches/.test(store) && /recentSearchScope/.test(store),
  ],
  ["recent searches are capped", /RECENT_SEARCH_LIMIT\s*=\s*10/.test(store)],
  ["sensitive history is filtered", /SENSITIVE_QUERY_PATTERN/.test(store)],
  ["search API uses internal endpoint", /get\("\/sites\/search"/.test(api)],
  [
    "suggest API uses internal endpoint",
    /get\("\/sites\/search\/suggest"/.test(api),
  ],
  ["search response supports pagination", /pagination/.test(results)],
  ["URL contains search query", /query = \{ q: state\.q \}/.test(results)],
  ["URL supports page", /query\.page = String\(state\.page\)/.test(results)],
  ["URL supports category", /query\.category = state\.category/.test(results)],
  ["URL supports sort", /query\.sort = state\.sort/.test(results)],
  [
    "browser route changes are watched",
    /watch\(\s*\(\) => route\.fullPath/.test(results),
  ],
  ["search cache lasts five minutes", /5 \* 60 \* 1000/.test(store)],
  [
    "cache key includes data version",
    /params\.sort,[\s\S]*dataVersion/.test(store),
  ],
  ["cache keeps stale payload", /if \(cachedPayload\)/.test(store)],
  [
    "results are not persisted locally",
    !/localStorage\.setItem\([^;]*resultsByKey/.test(store),
  ],
  ["network errors are distinct", /无法连接搜索服务/.test(store)],
  ["timeout errors are distinct", /搜索请求超时/.test(store)],
  ["503 errors are distinct", /搜索服务暂时不可用/.test(store)],
  [
    "empty state has commands",
    /清除关键词/.test(results) && /查看全部分类/.test(results),
  ],
  ["error state retries", /retrySearch/.test(results)],
  ["result list reuses site cards", /<SiteList :sites="sites"/.test(results)],
  [
    "search cards hide bottom actions",
    /<SiteList :sites="sites" hide-actions @visit="visit"/.test(results) &&
      /:hide-actions="hideActions"/.test(siteList),
  ],
  [
    "search filters use custom dark dropdowns",
    (results.match(/<SearchFilterDropdown/g) || []).length === 2 &&
      !/<select/.test(results) &&
      /role="listbox"/.test(filterDropdown) &&
      /max-height: 320px/.test(filterDropdown),
  ],
  [
    "dropdown keyboard and outside close are supported",
    /ArrowDown/.test(filterDropdown) &&
      /ArrowUp/.test(filterDropdown) &&
      /Escape/.test(filterDropdown) &&
      /handleOutsideClick/.test(filterDropdown),
  ],
  [
    "search result cards are immediately visible",
    /\.site-card-reveal\.reveal-on-scroll\)[\s\S]*opacity:\s*1;[\s\S]*transform:\s*none;/.test(
      results,
    ),
  ],
  ["favorite control remains in cards", /<FavoriteStarButton/.test(card)],
  ["visit is separate from favorite", /@visit="visit"/.test(results)],
  ["responsive four-column grid", /repeat\(4, minmax/.test(results)],
  ["responsive two-column grid", /repeat\(2, minmax/.test(results)],
  ["responsive one-column grid", /grid-template-columns: 1fr/.test(results)],
  ["package script is registered", packageJson.includes('"test:site-search"')],
];

let failures = 0;
for (const [name, passed] of checks) {
  if (passed) console.log(`PASS ${name}`);
  else {
    failures += 1;
    console.error(`FAIL ${name}`);
  }
}
if (failures) process.exit(1);
console.log(`站内搜索静态验收通过：${checks.length} 项。`);
