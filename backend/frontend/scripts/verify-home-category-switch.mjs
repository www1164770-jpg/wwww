import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) =>
  readFileSync(resolve(root, relativePath), "utf8");

const category = read("src/components/home/CategorySection.vue");
const siteCard = read("src/components/site/SiteCard.vue");
const api = read("src/utils/api.js");

assert.match(
  category,
  /const PAGE_SIZE = 15;[\s\S]*?const activeCategory = ref\("全部"\);[\s\S]*?const currentBatch = ref\(0\);/,
  "首页分类必须默认选中全部，并从第 0 批开始分页",
);
assert.match(
  category,
  /const filteredWebsites = computed\([\s\S]*?const list = Array\.isArray\(allWebsites\.value\) \? allWebsites\.value : \[\][\s\S]*?return list\.filter\([\s\S]*?getWebsiteCategoryKey\(website\) === categoryKey/,
  "分类筛选必须基于已加载网站数组和规范化分类键",
);
assert.match(
  category,
  /normalized === "all"[\s\S]*?normalized === "全部"/,
  "中文默认分类全部必须与规范化的 all 使用同一个筛选分支",
);
assert.match(
  category,
  /const totalBatches = computed\(\(\) =>\s*Math\.ceil\(filteredWebsites\.value\.length \/ PAGE_SIZE\),\s*\);/,
  "总批次数必须根据筛选结果和 PAGE_SIZE 计算",
);
assert.match(
  category,
  /const renderedWebsites = computed\(\(\) =>\s*\{\s*const start = currentBatch\.value \* PAGE_SIZE;\s*return filteredWebsites\.value\.slice\(start, start \+ PAGE_SIZE\);\s*\}\);/,
  "渲染数组必须按 currentBatch × PAGE_SIZE 切片，并且每批最多 PAGE_SIZE 条",
);
assert.match(
  category,
  /function handleCategoryChange\(categoryName\)\s*\{\s*if \(activeCategory\.value === categoryName\) return;\s*contentHasChanged\.value = true;\s*activeCategory\.value = categoryName;\s*currentBatch\.value = 0;/,
  "切换分类必须保留已加载数据，并将分页批次重置为第 0 批",
);
assert.match(
  category,
  /function changeWebsiteBatch\(\)\s*\{\s*if \(totalBatches\.value <= 1\) return;\s*contentHasChanged\.value = true;\s*currentBatch\.value = \(currentBatch\.value \+ 1\) % totalBatches\.value;/,
  "换一批必须在有效批次数内循环切换 currentBatch",
);
assert.match(
  category,
  /watch\(totalBatches, \(batchCount\) =>\s*\{\s*if \(currentBatch\.value >= batchCount\) currentBatch\.value = 0;\s*\}\);/,
  "筛选结果减少导致当前批次越界时，必须回到第 0 批",
);
for (const forbidden of [
  "allWebsites.value = []",
  "renderedWebsites.value = []",
  "categorySitesMap.value = {}",
  "location.reload",
  "loadCategorySites(",
]) {
  assert.ok(
    !category.includes(forbidden),
    `分类组件不应在筛选时清空或重新请求网站数据：${forbidden}`,
  );
}
assert.ok(
  !category.includes("<Transition"),
  "首页纯网格区域不应由 out-in 过渡暂时移除唯一网格",
);
assert.match(
  siteCard,
  /'reveal-on-scroll':\s*\(!isCategoryVariant && !isCareerVariant\) \|\| selectable/,
  "首页静态分类卡片必须跳过全局滚动显隐状态",
);
assert.match(
  api,
  /export function normalizeWebsite\(site = \{\}\)[\s\S]*?const normalizedId = String\(id\)[\s\S]*?renderKey/,
  "网站卡片必须使用稳定的规范化渲染键",
);
assert.match(
  api,
  /export function normalizeStringArray\(value\)/,
  "缺省标签和职业数组必须安全规范化",
);

console.log("首页分类切换渲染链路回归检查通过。");
