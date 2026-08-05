import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) =>
  readFileSync(resolve(root, relativePath), "utf8");
const detail = read("src/views/CategoryDetail.vue");
const card = read("src/components/site/SiteCard.vue");
const packageJson = JSON.parse(read("package.json"));

const checks = [
  ["默认分类为全部", /const activeCategory = ref\("全部"\)/],
  [
    "包含全部六个业务分类",
    [
      "开发文档",
      "AI 工具",
      "设计灵感",
      "学习资源",
      "开发社区",
      "效率工具",
    ].every((label) => detail.includes(`label: "${label}"`)),
  ],
  [
    "分类使用真实 button 并同步 aria-pressed",
    /<button[\s\S]*?class="category-tab"[\s\S]*?:aria-pressed="activeCategory === category\.label"/,
  ],
  [
    "分类筛选基于网站分类字段",
    /const filteredWebsites = computed\([\s\S]*?websites\.value\.filter\([\s\S]*?matchesCategory/.test(
      detail,
    ) &&
      /function getWebsiteCategory\([\s\S]*?website\.category_name/.test(
        detail,
      ),
  ],
  [
    "切换分类会清空已展开网站",
    /function handleCategoryChange\([\s\S]*?activeCategory\.value = categoryLabel[\s\S]*?selectedWebsiteId\.value = null/,
  ],
  [
    "卡片可选中且点击事件进入页面状态",
    /variant="category"[\s\S]*?selectable[\s\S]*?@select="handleWebsiteClick"/,
  ],
  [
    "再次点击同一网站会收起",
    /function handleWebsiteClick\([\s\S]*?selectedWebsiteId\.value === key \? null : key/,
  ],
  [
    "详情状态使用左侧列表与右侧详情",
    /class="website-detail-layout"[\s\S]*?class="website-detail-sidebar"[\s\S]*?class="website-detail-card"/,
  ],
  [
    "详情列表点击其他网站仍停留在详情布局",
    /class="website-detail-list-item"[\s\S]*?@click="handleWebsiteClick\(website\)"/,
  ],
  [
    "详情收起按钮具有清晰 aria-label",
    /class="collapse-detail-button"[\s\S]*?aria-label="收起网站详情"[\s\S]*?再次点击可收起/,
  ],
  [
    "官网入口使用新标签页安全打开",
    /class="website-visit-button"[\s\S]*?target="_blank"[\s\S]*?rel="noopener noreferrer"/,
  ],
  [
    "可选详情字段缺失时隐藏模块",
    /v-if="selectedWebsiteFeatures\.length"[\s\S]*?v-if="selectedWebsiteUrl \|\| selectedWebsiteAudiences\.length"[\s\S]*?v-if="selectedWebsiteScreenshots\.length"/,
  ],
  [
    "卡片支持键盘操作和展开状态",
    /:role="selectable \? 'button' : undefined"/.test(card) &&
      /:tabindex="selectable \? 0 : undefined"/.test(card) &&
      /@keydown\.enter\.prevent="handleCardClick"/.test(card) &&
      /@keydown\.space\.prevent="handleCardClick"/.test(card) &&
      /:aria-expanded="selectable \? selected : undefined"/.test(card),
  ],
  [
    "移动端详情布局与分类栏允许滚动",
    /\.category-nav\s*\{[\s\S]*?overflow-x:\s*auto[\s\S]*?@media \(max-width:\s*900px\)[\s\S]*?\.website-detail-layout\s*\{[\s\S]*?grid-template-columns:\s*1fr;/,
  ],
  [
    "支持减少动态效果",
    /@media \(prefers-reduced-motion:\s*reduce\)[\s\S]*?transition:\s*none/,
  ],
];

let failed = 0;
for (const [name, check] of checks) {
  const passed =
    check instanceof RegExp ? check.test(detail) || check.test(card) : check;
  if (passed) {
    console.log(`PASS ${name}`);
  } else {
    failed += 1;
    console.error(`FAIL ${name}`);
  }
}

if (
  packageJson.scripts?.["test:category-website-interactions"] !==
  "node scripts/verify-category-website-interactions.mjs"
) {
  failed += 1;
  console.error("FAIL 分类交互专项验收命令已注册");
}

if (failed) {
  console.error(`\n${failed} category website interaction check(s) failed.`);
  process.exit(1);
}

console.log("网站分类交互静态验收通过。");
