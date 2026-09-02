import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { websiteCatalog } from "../src/data/websiteCatalog.js";
import {
  COMMON_TOOL_CATEGORY_IDS,
  createCommonToolsQueue,
  dedupeCommonTools,
  getCommonToolKey,
  isEligibleCommonTool,
  takeNextCommonToolsBatch,
} from "../src/utils/commonToolsRotation.js";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) =>
  readFileSync(resolve(root, relativePath), "utf8");
const home = read("src/views/Home.vue");
const favoriteStack = read("src/components/home/FavoriteStack.vue");
const packageJson = JSON.parse(read("package.json"));
const fadeAnimationStart = favoriteStack.indexOf(
  "@keyframes common-tools-fade-in",
);
const fadeAnimationEnd = favoriteStack.indexOf(
  ".compact-tool-card",
  fadeAnimationStart,
);
const fadeAnimation = favoriteStack.slice(fadeAnimationStart, fadeAnimationEnd);

const makeRandom = (initialSeed = 123456789) => {
  let seed = initialSeed >>> 0;
  return () => {
    seed = (1664525 * seed + 1013904223) >>> 0;
    return seed / 2 ** 32;
  };
};

const samplePool = Array.from({ length: 12 }, (_, index) => ({
  id: index + 1,
  name: `Tool ${index + 1}`,
  url: `https://tool-${index + 1}.example.com`,
}));
const random = makeRandom();
let shuffled = createCommonToolsQueue(samplePool, [], random);
let cursor = 0;
let previousBatch = [];
const batches = [];
for (let index = 0; index < 5; index += 1) {
  const next = takeNextCommonToolsBatch({
    candidates: samplePool,
    shuffled,
    cursor,
    previousBatch,
    batchSize: 4,
    random,
  });
  batches.push(next.batch);
  shuffled = next.shuffled;
  cursor = next.cursor;
  previousBatch = next.batch;
}

const firstRoundKeys = new Set(
  batches.slice(0, 3).flat().map(getCommonToolKey),
);
const consecutiveBatchesAreDisjoint = batches.every((batch, index) => {
  if (!index) return true;
  const previousKeys = new Set(batches[index - 1].map(getCommonToolKey));
  return batch.every((site) => !previousKeys.has(getCommonToolKey(site)));
});
const smallPoolBatch = takeNextCommonToolsBatch({
  candidates: samplePool.slice(0, 2),
  batchSize: 4,
  random: makeRandom(7),
}).batch;
const dedupedPool = dedupeCommonTools([
  samplePool[0],
  { ...samplePool[0], id: 999 },
  samplePool[1],
]);
const baseCandidateCount = websiteCatalog.filter(isEligibleCommonTool).length;

const checks = [
  [
    "The existing catalog provides a substantial common-tools candidate pool",
    baseCandidateCount >= 12 && COMMON_TOOL_CATEGORY_IDS.size === 9,
  ],
  [
    "Entertainment-oriented common-category sites stay outside the tool pool",
    ["哔哩哔哩", "腾讯视频", "喜马拉雅"].every(
      (name) =>
        !websiteCatalog
          .filter((site) => site.name === name)
          .some(isEligibleCommonTool),
    ),
  ],
  [
    "Fisher-Yates queues yield four unique sites per desktop batch",
    batches.every(
      (batch) =>
        batch.length === 4 &&
        new Set(batch.map(getCommonToolKey)).size === batch.length,
    ),
  ],
  [
    "One full shuffled round presents every candidate once",
    firstRoundKeys.size === samplePool.length,
  ],
  [
    "Adjacent batches stay completely different when the pool is large enough",
    consecutiveBatchesAreDisjoint,
  ],
  [
    "A pool smaller than four is not padded with duplicate sites",
    smallPoolBatch.length === 2 &&
      new Set(smallPoolBatch.map(getCommonToolKey)).size === 2,
  ],
  [
    "Duplicate URLs are removed even when source records use different IDs",
    dedupedPool.length === 2,
  ],
  [
    "The common-tools screen renders the current website-object batch",
    home.includes('<FavoriteStack :sites="currentCommonTools"') &&
      home.includes('v-if="commonToolsCandidatePool.length"'),
  ],
  [
    "Runtime responses enrich catalog matches without adding unknown extras",
    home.includes("return dedupeCommonTools(catalogSites).filter(") &&
      !home.includes("...runtimeByKey.values()"),
  ],
  [
    "A dedicated observer advances only on the 65-percent enter edge",
    home.includes("const COMMON_TOOLS_ENTER_RATIO = 0.65") &&
      home.includes("entry.intersectionRatio >= COMMON_TOOLS_ENTER_RATIO") &&
      home.includes(
        "if (isVisible === commonToolsSectionVisible.value) return",
      ) &&
      home.includes("if (isVisible) showNextCommonToolsBatch()"),
  ],
  [
    "Common tool cards remain capped at four and use only a short opacity fade",
    favoriteStack.includes(".slice(0, 4)") &&
      favoriteStack.includes("common-tools-fade-in 180ms") &&
      fadeAnimation.includes("opacity: 0") &&
      fadeAnimation.includes("opacity: 1") &&
      !fadeAnimation.includes("transform:"),
  ],
  [
    "The专项 verifier is registered as an npm script",
    packageJson.scripts?.["test:common-tools-rotation"] ===
      "node scripts/verify-common-tools-rotation.mjs",
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

console.log(`INFO base common-tools candidates: ${baseCandidateCount}`);
if (failed) {
  console.error(`\n${failed} common-tools rotation check(s) failed.`);
  process.exit(1);
}
