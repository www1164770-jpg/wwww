import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const projectRoot = resolve(frontendRoot, "..", "..");
const readFrontend = (file) =>
  readFileSync(resolve(frontendRoot, file), "utf8");
const readProject = (file) => readFileSync(resolve(projectRoot, file), "utf8");

const visitUtil = readFrontend("src/utils/siteVisit.js");
const api = readFrontend("src/utils/api.js");
const profile = readFrontend("src/views/ProfileView.vue");
const home = readFrontend("src/views/Home.vue");
const search = readFrontend("src/views/SearchResults.vue");
const favorites = readFrontend("src/views/Favorites.vue");
const category = readFrontend("src/views/CategoryDetail.vue");
const siteDetail = readFrontend("src/views/SiteDetail.vue");
const marquee = readFrontend("src/components/home/ToolMarquee.vue");
const recommend = readFrontend("src/components/home/RecommendSection.vue");
const siteCard = readFrontend("src/components/site/SiteCard.vue");
const backend = readProject("backend/app.py");
const packageJson = JSON.parse(readFrontend("package.json"));

const pageSources = [home, search, favorites, category, siteDetail];
const directOpenOutsideUtility = pageSources.some((source) =>
  /window\.open\s*\(/.test(source),
);

const openIndex = visitUtil.indexOf("window.open(url");
const recordIndex = visitUtil.indexOf("void recordBrowsingHistory");

const checks = [
  [
    "The unified visit helper opens a new tab before awaiting persistence",
    openIndex >= 0 && recordIndex > openIndex,
  ],
  [
    "History is stored locally before authenticated server synchronization",
    /saveLocalBrowsingHistory\(item\)[\s\S]*?hasAuthenticatedSession/.test(
      visitUtil,
    ),
  ],
  [
    "Guest visits are retained without a fabricated user id",
    /if \(!hasAuthenticatedSession\(\)\) return Promise\.resolve\(item\)/.test(
      visitUtil,
    ) &&
      /def record_user_history\(\):[\s\S]*?user = get_history_user\(\)/.test(
        backend,
      ) &&
      !/def record_user_history\(\):[\s\S]{0,300}get_current_username/.test(
        backend,
      ),
  ],
  [
    "Repeated visits are deduplicated within thirty seconds",
    /BROWSING_HISTORY_DEDUPE_MS = 30_000/.test(visitUtil) &&
      /DATE_SUB\(NOW\(\), INTERVAL 30 SECOND\)/.test(backend),
  ],
  [
    "The API layer normalizes supported history response shapes",
    /normalizeHistoryResponse/.test(api) &&
      /data\?\.items/.test(api) &&
      /data\?\.history/.test(api) &&
      /data\?\.records/.test(api),
  ],
  [
    "The backend reads and writes visit events for the JWT user",
    /@app\.route\('\/api\/user\/history', methods=\['POST'\]\)[\s\S]*?@jwt_required\(\)/.test(
      backend,
    ) &&
      /INSERT INTO user_behaviors[\s\S]*?'visit'/.test(backend) &&
      /WHERE ub\.user_id = %s AND ub\.behavior_type = 'visit'/.test(backend),
  ],
  [
    "The backend supports deleting one record and clearing all records",
    /\/api\/user\/history\/<int:history_id>/.test(backend) &&
      /DELETE FROM user_behaviors[\s\S]*?behavior_type='visit'/.test(backend),
  ],
  [
    "Major page entry points call the unified helper",
    pageSources.every((source) => /utils\/siteVisit/.test(source)) &&
      !directOpenOutsideUtility,
  ],
  [
    "Semantic home links track normal, modified, and middle clicks",
    /@click="recordVisit\(site, \$event\)"/.test(marquee) &&
      /@auxclick\.middle="recordVisit\(site, \$event\)"/.test(marquee) &&
      /@click="recordVisit\(site, \$event\)"/.test(recommend),
  ],
  [
    "Site cards route external actions through their visit event",
    /website-card__external[\s\S]*?@click\.stop\.prevent="openSite"/.test(
      siteCard,
    ),
  ],
  [
    "The history view loads real records and only shows empty state for an empty list",
    /loadBrowsingHistory\(\)/.test(profile) &&
      /!historyItems\.length/.test(profile) &&
      /v-for="item in historyItems"/.test(profile),
  ],
  [
    "The history view supports retry, revisit, single delete, and clear",
    /@click="loadHistory"/.test(profile) &&
      /visitHistoryItem/.test(profile) &&
      /deleteBrowsingHistory/.test(profile) &&
      /clearBrowsingHistory/.test(profile) &&
      /window\.confirm/.test(profile),
  ],
  [
    "The browsing history verifier is registered as an npm script",
    packageJson.scripts?.["test:browsing-history"] ===
      "node scripts/verify-browsing-history.mjs",
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
  console.error(`\n${failed} browsing history verification check(s) failed.`);
  process.exit(1);
}
