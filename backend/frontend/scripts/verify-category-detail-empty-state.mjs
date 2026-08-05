import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) =>
  readFileSync(resolve(root, relativePath), "utf8");
const detail = read("src/views/CategoryDetail.vue");
const packageJson = JSON.parse(read("package.json"));

const checks = [
  [
    "分类栏为透明毛玻璃且横向紧凑",
    /\.category-nav\s*\{[\s\S]*?overflow-x:\s*auto/.test(detail) &&
      /\.category-nav,[\s\S]*?backdrop-filter:\s*blur\(18px\)/.test(detail),
  ],
  [
    "详情页桌面端为左右两栏",
    /\.website-detail-layout\s*\{[\s\S]*?grid-template-columns:\s*minmax\(250px, 30%\)\s+minmax\(0, 1fr\)/,
  ],
  [
    "移动端详情切换为单栏",
    /@media \(max-width:\s*900px\)[\s\S]*?\.website-detail-layout\s*\{[\s\S]*?grid-template-columns:\s*1fr;/,
  ],
  [
    "加载态不会渲染为空态",
    /v-if="isInitialLoading && websites\.length === 0"/.test(detail) &&
      /aria-busy="loading \? 'true' : 'false'"/.test(detail),
  ],
  ["错误态与空态分离", /<CategoryErrorState[\s\S]*?该分类暂无网站资源/],
  ["空分类使用统一文案", /<h2>该分类暂无网站资源<\/h2>/],
  [
    "清除筛选会重置字段并同步路由",
    /async function clearFilters\(\)[\s\S]*?category_id:\s*""[\s\S]*?sort:\s*DEFAULT_SORT[\s\S]*?syncFiltersToRoute\(\)[\s\S]*?loadSites\(filters\)/,
  ],
  [
    "切换分类自动退出详情",
    /function handleCategoryChange\([\s\S]*?selectedWebsiteId\.value = null/,
  ],
  [
    "自定义详情字段为空时隐藏模块",
    /v-if="selectedWebsiteFeatures\.length"[\s\S]*?v-if="selectedWebsiteScreenshots\.length"/,
  ],
  [
    "减少动态效果时关闭过渡",
    /@media \(prefers-reduced-motion:\s*reduce\)[\s\S]*?transition:\s*none/,
  ],
  [
    "专项验证命令已注册",
    packageJson.scripts?.["test:category-empty-state"] ===
      "node scripts/verify-category-detail-empty-state.mjs",
  ],
];

let failed = 0;
for (const [name, check] of checks) {
  const passed = check instanceof RegExp ? check.test(detail) : check;
  if (passed) {
    console.log(`PASS ${name}`);
  } else {
    failed += 1;
    console.error(`FAIL ${name}`);
  }
}

if (failed) {
  console.error(`\n${failed} category detail verification check(s) failed.`);
  process.exit(1);
}

console.log("分类详情页布局与空状态静态验收通过。");
