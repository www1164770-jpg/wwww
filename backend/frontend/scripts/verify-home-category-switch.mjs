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
  /const activeCategory = ref\("全部"\)[\s\S]*?const visibleLimit = ref\(PAGE_SIZE\)/,
  "首页分类必须默认选中全部，并初始化分页数量",
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
  /const renderedWebsites = computed\(\(\) =>\s*filteredWebsites\.value\.slice\(0, normalizedVisibleLimit\.value\)/,
  "渲染数组必须由过滤数组稳定切片得到",
);
assert.match(
  category,
  /function handleCategoryChange\(categoryName\)\s*\{\s*activeCategory\.value = categoryName;\s*visibleLimit\.value = PAGE_SIZE;/,
  "切换分类必须只更新分类和可见数量",
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
