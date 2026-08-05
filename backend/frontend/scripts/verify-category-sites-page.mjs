import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const detail = readFileSync(
  resolve(root, "src/views/CategoryDetail.vue"),
  "utf8",
);
const card = readFileSync(
  resolve(root, "src/components/site/SiteCard.vue"),
  "utf8",
);
const packageJson = readFileSync(resolve(root, "package.json"), "utf8");

const checks = [
  ["分类详情页存在分类栏", /<nav class="category-nav"[\s\S]*?网站分类/],
  ["默认使用网站卡片网格", /class="category-site-grid"[\s\S]*?<SiteCard\b/],
  ["复用网站卡片组件", /import SiteCard/],
  ["保留更多筛选能力", /<SiteFilter\b[\s\S]*?@change="handleFilterChange"/],
  [
    "加载态不会误判为空态",
    /v-if="isInitialLoading && websites\.length === 0"[\s\S]*?v-else-if="error && websites\.length === 0"/,
  ],
  ["错误状态可重试", /<CategoryErrorState[\s\S]*?@retry="loadSites"/],
  ["分类无资源显示统一空态", /该分类暂无网站资源/],
  [
    "网站列表 API 支持分页拉取",
    /async function fetchAllSites[\s\S]*?siteAPI\.getSites/,
  ],
  [
    "卡片与详情使用淡入淡出切换",
    /<Transition name="view-switch" mode="out-in">/,
  ],
  [
    "详情页存在左列表与右详情",
    /website-detail-sidebar[\s\S]*?website-detail-card/,
  ],
  ["分类页卡片不直接显示官网动作", /variant="category"[\s\S]*?hide-actions/],
  [
    "分类页卡片支持键盘交互",
    /@keydown\.enter\.prevent="handleCardClick"[\s\S]*?@keydown\.space\.prevent="handleCardClick"/,
  ],
  ["专项验证命令已注册", packageJson.includes('"test:category-sites-page"')],
];

const failures = checks
  .filter(([, pattern]) =>
    pattern instanceof RegExp ? !pattern.test(detail + card) : !pattern,
  )
  .map(([name]) => name);

if (failures.length) {
  console.error("分类详情页网站列表静态验收失败：");
  failures.forEach((name) => console.error(`- ${name}`));
  process.exit(1);
}

console.log("分类详情页网站列表静态验收通过。");
