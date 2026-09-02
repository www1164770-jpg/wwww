import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const categorySection = readFileSync(
  resolve(root, "src/components/home/CategorySection.vue"),
  "utf8",
);
const siteCard = readFileSync(
  resolve(root, "src/components/site/SiteCard.vue"),
  "utf8",
);
const home = readFileSync(resolve(root, "src/views/Home.vue"), "utf8");

assert.doesNotMatch(
  categorySection,
  /visibleWebsiteCount|个网站/,
  "首页分类状态不应暴露数据库网站数量",
);

assert.match(
  categorySection,
  /from "lucide-vue-next"/,
  "首页分类栏应使用现有图标库",
);
assert.match(
  categorySection,
  /const activeCategory = ref\("全部"\)/,
  "首页分类默认应选中全部",
);
assert.match(
  categorySection,
  /const categoryOptions = computed[\s\S]*?props\.categories\.forEach\(addCategory\)/,
  "首页分类按钮应来自接口分类数据",
);
assert.match(
  categorySection,
  /<nav class="category-nav"[\s\S]*?<button[\s\S]*?:aria-pressed="activeCategory === category\.name"/,
  "分类栏应使用真实 button 和 aria-pressed",
);
assert.match(
  categorySection,
  /const filteredWebsites = computed[\s\S]*?getWebsiteCategoryKey\(website\) === categoryKey/,
  "筛选应基于网站分类字段",
);
assert.match(
  categorySection,
  /function getWebsiteCategoryName[\s\S]*?categoryId[\s\S]*?category_id[\s\S]*?category_name/,
  "筛选应兼容现有分类字段",
);
assert.match(
  categorySection,
  /class="website-card-grid"[\s\S]*?<SiteCard[\s\S]*?variant="category"[\s\S]*?hide-actions/,
  "首页应渲染网站级卡片网格",
);
assert.match(
  categorySection,
  /const PAGE_SIZE = 20[\s\S]*?visibleLimit = ref\(PAGE_SIZE\)/,
  "首页分类首批应按 5 列网格显示 4 行，共 20 个网站",
);
assert.match(
  categorySection,
  /const normalizedVisibleLimit = computed\([\s\S]*?Number\(visibleLimit\.value\)[\s\S]*?Number\.isFinite\([\s\S]*?const renderedWebsites = computed\(/,
  "网站网格的可见数量必须始终是有效正数",
);
assert.match(
  categorySection,
  /<div v-if="filteredWebsites\.length" class="website-card-grid">[\s\S]*?v-for="website in renderedWebsites"/,
  "分类切换后应直接渲染当前过滤结果",
);
assert.match(
  categorySection,
  /function handleCategoryChange[\s\S]*?visibleLimit\.value = PAGE_SIZE/,
  "切换分类应只更新筛选和显示数量",
);
assert.match(
  siteCard,
  /website-card--category-static[\s\S]*?function handleCardClick\(\)[\s\S]*?isCompactCategoryVariant\.value\) openSite\(\)[\s\S]*?emit\("visit", \{ \.\.\.props\.site, url: normalizedSiteUrl\.value \}\)/,
  "分类卡片应保留当前统一的安全访问事件",
);
assert.match(
  categorySection,
  /\.category-filter-bar\s*\{[\s\S]*?background:\s*transparent[\s\S]*?box-shadow:\s*none/,
  "分类栏外层应透明且不制造阴影分层",
);
assert.match(
  categorySection,
  /\.category-tab\s*\{[\s\S]*?border:\s*0[\s\S]*?background:\s*transparent/,
  "未选中分类按钮应保持透明无边框",
);
assert.match(
  categorySection,
  /\.category-tab--active,[\s\S]*?background:\s*var\(--app-tab-active-bg\)[\s\S]*?box-shadow:\s*none/,
  "选中分类按钮应只使用轻量自适应高亮",
);
assert.match(
  categorySection,
  /grid-template-columns:\s*repeat\(5, minmax\(0, 1fr\)\)/,
  "桌面端分类网格应固定为 5 列",
);
for (const [breakpoint, columns] of [
  [1200, 4],
  [960, 3],
  [720, 2],
  [480, 1],
]) {
  assert.match(
    categorySection,
    new RegExp(
      `@media \\(max-width:\\s*${breakpoint}px\\)[\\s\\S]*?grid-template-columns:\\s*${columns === 1 ? "minmax\\(0, 1fr\\)" : `repeat\\(${columns}, minmax\\(0, 1fr\\)\\)`}`,
    ),
    `分类网格应在 ${breakpoint}px 切换为 ${columns} 列`,
  );
}
assert.match(
  categorySection,
  /@media \(prefers-reduced-motion:\s*reduce\)/,
  "首页分类区域应支持减少动态效果",
);
assert.match(
  siteCard,
  /'reveal-on-scroll':\s*\(!isCategoryVariant && !isCareerVariant\) \|\| selectable/,
  "静态首页分类卡片不应继承会阻断渲染的滚动显隐样式",
);

["category-card", "category-site__detail", "category-more", "查看更多"].forEach(
  (legacyToken) => {
    assert.ok(
      !categorySection.includes(legacyToken),
      `首页分类区域不应继续渲染旧结构：${legacyToken}`,
    );
  },
);
for (const legacyToken of [
  "selectedWebsiteId",
  "selectedWebsite",
  "isDetailOpen",
  "website-detail-layout",
  "collapse-detail-button",
  "category-view-switch",
]) {
  assert.ok(
    !categorySection.includes(legacyToken),
    `首页分类区域不应继续保留详情交互：${legacyToken}`,
  );
}

assert.match(home, /id="tools"[\s\S]*?data-testid="popular-categories"/);
assert.ok(!home.includes('id="categories"'), "首页分类区域应使用 #tools 锚点");
assert.match(
  home,
  /return unwrapList\(response\)\.filter\(\(item\) => !item\.parent_id\)/,
  "首页分类不应将接口结果截断为固定六项",
);

console.log("首页网站分类区域静态验收通过。");
