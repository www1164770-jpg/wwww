import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) =>
  readFileSync(resolve(root, relativePath), "utf8");

const footer = read("src/components/layout/AppFooter.vue");
const home = read("src/views/Home.vue");
const publicViews = [
  "src/views/Categories.vue",
  "src/views/CategoryDetail.vue",
  "src/views/SearchResults.vue",
  "src/views/SiteDetail.vue",
].map(read);
const restrictedViews = [
  "src/views/Login.vue",
  "src/views/Register.vue",
  "src/views/Admin.vue",
].map(read);
const router = read("src/router/index.js");
const packageJson = JSON.parse(read("package.json"));
const footerStyles = footer.split("<style scoped>")[1] || "";
const appFooterRule =
  footerStyles.match(/\.app-footer\s*\{([^}]*)\}/)?.[1] || "";

const routePaths = new Set(
  [...router.matchAll(/path:\s*["']([^"']+)["']/g)].map((match) => match[1]),
);
const footerTargets = [
  ...footer.matchAll(
    /\{\s*label:\s*["'][^"']+["'],\s*to:\s*["']([^"']+)["']\s*\}/g,
  ),
].map((match) => match[1]);

const checks = [
  ["使用语义化 footer 元素", /<footer\b/.test(footer)],
  [
    "品牌区包含 Header 同源 Logo、品牌名和非空简介",
    footer.includes('src="/vocanav-logo.png"') &&
      footer.includes("知航屿") &&
      /app-footer__description[\s\S]*?精选高质量/.test(footer),
  ],
  [
    "快速链接使用带无障碍名称的 nav",
    footer.includes(
      '<nav class="app-footer__section" aria-label="页脚快速链接">',
    ),
  ],
  [
    "站内链接统一使用 RouterLink",
    footer.includes("<RouterLink") &&
      !/<a\b[^>]*href=/.test(footer) &&
      !footer.includes('href="#"'),
  ],
  [
    "所有 Footer 链接目标均来自真实路由",
    footerTargets.length === 5 &&
      footerTargets.every((target) => routePaths.has(target)),
  ],
  [
    "相关信息仅展示真实存在的版权申诉入口",
    footer.includes('{ label: "版权申诉", to: "/dmca" }') &&
      routePaths.has("/dmca"),
  ],
  [
    "桌面端使用三列 Grid，平板降为两列",
    /grid-template-columns:\s*\n?\s*minmax\(280px, 1\.6fr\)[\s\S]*?minmax\(180px, 0\.9fr\)/.test(
      footer,
    ) && /@media \(max-width: 800px\)[\s\S]*?repeat\(2, minmax/.test(footer),
  ],
  [
    "手机端降为单列且品牌区取消跨列",
    /@media \(max-width: 560px\)[\s\S]*?grid-template-columns: 1fr[\s\S]*?grid-column: auto/.test(
      footer,
    ),
  ],
  [
    "Footer 使用浅色背景和顶部边界",
    /\.app-footer\s*\{[\s\S]*?border-top:[\s\S]*?background: var\(--color-soft\)/.test(
      footer,
    ),
  ],
  [
    "链接和品牌入口提供可见焦点样式",
    footer.includes(":focus-visible") && footer.includes("outline-offset: 3px"),
  ],
  [
    "版权年份动态生成",
    footer.includes("new Date().getFullYear()") &&
      !/版权所有\s*2026|©\s*2026/.test(footer),
  ],
  [
    "不包含备案或其他占位文案",
    !/(备案信息占位|ICP备案号|待补充|TODO|XXX占位|占位)/.test(footer),
  ],
  [
    "不新增 #tools 依赖，且不使用固定高度或隐藏溢出",
    !footer.includes("#tools") &&
      !/\b(?:min-)?height\s*:/.test(appFooterRule) &&
      !/overflow\s*:\s*hidden/.test(footerStyles),
  ],
  [
    "首页与公开内容页复用同一个 Footer，未创建第二个组件",
    home.includes(
      'import AppFooter from "../components/layout/AppFooter.vue"',
    ) &&
      home.includes("<AppFooter />") &&
      publicViews.every(
        (view) =>
          view.includes(
            'import AppFooter from "../components/layout/AppFooter.vue"',
          ) && view.includes("<AppFooter />"),
      ),
  ],
  [
    "登录、注册与后台不渲染公共 Footer",
    restrictedViews.every(
      (view) => !view.includes("AppFooter") && !view.includes("<footer"),
    ),
  ],
  [
    "专项验收命令已注册",
    packageJson.scripts?.["test:footer-layout"] ===
      "node scripts/verify-footer-layout.mjs",
  ],
];

let failed = 0;
for (const [name, passed] of checks) {
  if (passed) {
    console.log(`PASS ${name}`);
  } else {
    failed += 1;
    console.error(`FAIL ${name}`);
  }
}

if (failed) {
  console.error(`\n${failed} footer verification check(s) failed.`);
  process.exit(1);
}

console.log("Footer 布局与内容静态验收通过。");
