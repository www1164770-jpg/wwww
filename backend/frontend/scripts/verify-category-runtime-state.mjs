import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) =>
  readFileSync(resolve(root, relativePath), "utf8");

const api = read("src/utils/api.js");
const home = read("src/views/Home.vue");
const category = read("src/components/home/CategorySection.vue");
const categoryDetail = read("src/views/CategoryDetail.vue");
const loadCategoriesStart = home.indexOf("async function loadCategories(");
const loadCategoriesEnd = home.indexOf("async function retryCategories");
const loadCategories = home.slice(loadCategoriesStart, loadCategoriesEnd);
const beforeCategoryResponse = loadCategories.slice(
  0,
  loadCategories.indexOf("const categoryRequest"),
);

assert.ok(loadCategoriesStart >= 0, "Home.vue 缺少分类加载函数");
assert.ok(loadCategoriesEnd > loadCategoriesStart, "分类加载函数边界无效");

for (const snippet of [
  "const payload = response?.data ?? response",
  "payload?.data?.items",
  "payload?.data?.sites",
  "payload?.data?.results",
  "export function normalizeWebsite(site = {})",
  "export function normalizeWebsiteList(response)",
]) {
  assert.ok(api.includes(snippet), `api.js 缺少响应标准化兼容逻辑: ${snippet}`);
}

for (const snippet of [
  "let categoryRequestController = null",
  "let categoryRequestId = 0",
  "const requestId = ++categoryRequestId",
  "createCategoryRequestController(parentSignal)",
  "const retainedSiteMap = categorySitesMap.value",
  "const websiteRequest = loadCategorySites",
  "const [categoryResult, siteResult] = await Promise.all",
  "const retainedWebsites = flattenCategorySites(retainedSiteMap)",
  'categoryStatus.value = "error"',
  "categoryRequestController?.abort()",
]) {
  assert.ok(home.includes(snippet), `Home.vue 缺少请求状态保护: ${snippet}`);
}

assert.ok(
  !beforeCategoryResponse.includes("categorySitesMap.value = {}"),
  "刷新请求开始前不应清空已有网站卡片数据",
);
assert.ok(
  home.includes("const pageItems = normalizeWebsiteList(response)"),
  "分类网站接口必须使用统一网站响应标准化",
);

for (const snippet of [
  "const WEBSITE_PAGE_SIZE = 100",
  "const builtinWebsites = normalizeWebsiteList(websiteCatalog)",
  "restoreImmediateData()",
  "readWebsiteCache()",
  "writeWebsiteCache(nextWebsites)",
  "categorySitesMap.value = siteResult.map",
]) {
  assert.ok(
    home.includes(snippet),
    `Home.vue 缂哄皯璧勬簮鐩綍鎴栧師瀛樻暟鎹繚鐣欓€昏緫: ${snippet}`,
  );
}

for (const snippet of [
  "const nextWebsites = await fetchAllSites",
  "if (currentRequest !== requestSequence) return",
  "websites.value = nextWebsites",
  "const isInitialLoading = ref(false)",
  "const isRefreshing = ref(false)",
  "const hasLoadedSuccessfully = ref(false)",
  'v-if="isInitialLoading && websites.length === 0"',
  'v-if="isRefreshing || loading || error"',
  "FILTER_QUERY_KEYS.map((key) => queryValue(route.query[key]))",
  "onActivated(() =>",
  "requestSequence += 1",
]) {
  assert.ok(
    categoryDetail.includes(snippet),
    `CategoryDetail 缂哄皯璇锋眰绔炴€佹垨鍔犺浇鐘舵€佷繚鎶? ${snippet}`,
  );
}

assert.ok(
  !categoryDetail.includes("websites.value = await fetchAllSites"),
  "鏃ц姹備笉鑳藉湪 sequence 鏍￠獙鍓嶇洿鎺ュ啓鍏ョ綉绔欐暟缁?",
);

for (const snippet of [
  "status === 'loading' && !allWebsites.length",
  "status === 'error' && !allWebsites.length",
  "status === 'empty' && !allWebsites.length",
  "refreshing || loadingCategorySites",
  "error && allWebsites.length",
  "normalizeWebsite(website)",
  ':key="websiteKey(website)"',
  "const PAGE_SIZE = 25",
  "const renderedWebsites = computed(()",
  'variant="category"',
  "hide-actions",
  "website-load-more",
]) {
  assert.ok(
    category.includes(snippet),
    `CategorySection 缺少稳定状态渲染逻辑: ${snippet}`,
  );
}

for (const detailSnippet of [
  "selectedWebsiteId",
  "selectedWebsite",
  "isDetailOpen",
  "website-detail-layout",
  "collapseWebsiteDetail",
]) {
  assert.ok(
    !category.includes(detailSnippet),
    `首页分类组件不应继续维护详情状态: ${detailSnippet}`,
  );
}

console.log("分类运行时状态与响应标准化静态验收通过。");
