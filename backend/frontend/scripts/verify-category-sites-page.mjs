import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const detail = readFileSync(resolve(root, "src/views/CategoryDetail.vue"), "utf8");
const packageJson = readFileSync(resolve(root, "package.json"), "utf8");

const checks = [
  ["分类详情页存在右侧网站列表", /class="results-panel"[\s\S]*?class="category-site-grid"/],
  ["复用网站卡片", /import SiteCard/.test(detail) && /<SiteCard\b/.test(detail)],
  ["保留左侧筛选栏", /<aside class="filter-panel">[\s\S]*?<SiteFilter\b/],
  ["显示加载状态", /<LoadingState\s+v-if="loading"/],
  ["显示明确空状态", /当前分类下暂无匹配网站/],
  ["显示错误状态并可重试", /v-else-if="error"[\s\S]*?@click="loadSites"/],
  ["读取路由分类参数", /route\.params\.id/],
  ["筛选优先使用已选分类", /category_id:\s*source\.category_id\s*\|\|\s*route\.params\.id/],
  ["初始加载网站", /onMounted\([\s\S]*?await loadSites\(\)/],
  ["路由分类变化重新加载", /watch\([\s\S]*?route\.params\.id[\s\S]*?await loadSites\(\)/],
  ["调用网站列表 API", /siteAPI\.getSites\(cleanFilters\(nextFilters\)\)/],
  ["详情页激活网站卡片浮现动画", /function observeSiteCards\([\s\S]*?IntersectionObserver/],
  ["列表更新后注册浮现动画", /watch\(\s*sites[\s\S]*?observeSiteCards\(\)/],
];

const failures = checks
  .filter(([, pattern]) => (pattern instanceof RegExp ? !pattern.test(detail) : !pattern))
  .map(([name]) => name);

if (failures.length) {
  console.error("分类详情页静态验收失败：");
  failures.forEach((name) => console.error(`- ${name}`));
  process.exit(1);
}

if (!packageJson.includes('"test:category-sites-page"')) {
  console.error("package.json 未注册 test:category-sites-page");
  process.exit(1);
}

console.log("分类详情页网站列表静态验收通过。");
