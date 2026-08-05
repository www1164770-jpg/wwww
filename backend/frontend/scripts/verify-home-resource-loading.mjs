import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const home = readFileSync(resolve(root, "src/views/Home.vue"), "utf8");
const categorySection = readFileSync(
  resolve(root, "src/components/home/CategorySection.vue"),
  "utf8",
);
const api = readFileSync(resolve(root, "src/utils/api.js"), "utf8");

assert.ok(
  !home.includes('v-if="loading || error"'),
  "首页不应以全页 loading 阻塞分类区域",
);
assert.match(home, /new AbortController\(\)/, "首页请求应支持取消");
assert.match(
  home,
  /const HOME_RESOURCE_TIMEOUT_MS = 15_000/,
  "首页分类资源请求应预留聚合查询所需的合理超时",
);
assert.match(
  home,
  /timeout: HOME_RESOURCE_TIMEOUT_MS/,
  "分类与分类资源请求应共用首页资源超时配置",
);
assert.match(
  home,
  /<div class="home-content">[\s\S]*?<CategorySection/,
  "首页内容必须位于可渲染容器中，不能被原生 template 隐藏",
);
assert.match(home, /Promise\.allSettled/, "分类资源应独立完成");
assert.match(
  home,
  /const nextSiteMap = \{\}/,
  "分类预览应逐项发布，不等待全部分类完成",
);
const categoryLoader = home.slice(
  home.indexOf("async function loadCategorySites"),
  home.indexOf("async function loadCategories"),
);
assert.match(
  home,
  /categorySitesMap\.value = siteResult\.map/,
  "category data is committed atomically after website requests settle",
);
assert.ok(
  !categoryLoader.includes("siteAPI.getRandom") &&
    !categoryLoader.includes("categorySitesMap.value ="),
  "分类预览失败时不应再追加远程随机请求",
);
assert.match(
  categorySection,
  /class="website-skeleton-card"/,
  "分类请求中应显示局部骨架屏",
);
const restoreImmediateIndex = home.indexOf("restoreImmediateData();");
const initialRevealIndex = home.indexOf(
  "observeRevealElements();",
  restoreImmediateIndex,
);
const firstRemoteLoadIndex = home.indexOf(
  "await loadHome();",
  restoreImmediateIndex,
);
assert.ok(
  restoreImmediateIndex >= 0 &&
    initialRevealIndex > restoreImmediateIndex &&
    initialRevealIndex < firstRemoteLoadIndex,
  "本地网站数据恢复后必须先初始化可见性，不能等待远程请求完成",
);
assert.match(
  api,
  /export const API_TIMEOUT_MS = 15000/,
  "Axios 应设置统一超时",
);
assert.match(api, /pendingCategoriesRequest/, "分类请求应复用进行中的请求");

console.log("首页资源加载静态验收通过。");
