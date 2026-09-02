import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontendRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const projectRoot = resolve(frontendRoot, "..", "..");
const readFrontend = (file) =>
  readFileSync(resolve(frontendRoot, file), "utf8");
const readProject = (file) => readFileSync(resolve(projectRoot, file), "utf8");

const profile = readFrontend("src/views/ProfileView.vue");
const router = readFrontend("src/router/index.js");
const home = readFrontend("src/views/Home.vue");
const api = readFrontend("src/utils/api.js");
const backend = readProject("backend/v1_routes.py");
const emptyState = readFrontend("src/components/common/EmptyState.vue");
const loadingState = readFrontend("src/components/common/LoadingState.vue");

const nav = profile.match(
  /<nav aria-label="个人中心菜单">([\s\S]*?)<\/nav>/,
)?.[1];
assert.ok(nav, "个人中心菜单应存在");

const menuItems = [...nav.matchAll(/<a href="([^"]+)">([^<]+)<\/a>/g)].map(
  ([, href, label]) => ({ href, label: label.trim() }),
);
assert.deepEqual(menuItems, [
  { href: "#questionnaire", label: "我的问卷" },
  { href: "#favorites", label: "我的收藏" },
  { href: "#history", label: "浏览历史" },
  { href: "#password", label: "修改密码" },
]);

assert.doesNotMatch(
  profile,
  /我的推荐|#recommendations|profile\.recommendations/,
);
assert.doesNotMatch(profile, /SiteList|function visit\(site\)/);
for (const id of ["questionnaire", "favorites", "history", "password"]) {
  assert.match(profile, new RegExp(`<section id="${id}"`));
}
assert.match(profile, /grid-template-columns:\s*repeat\(4, max-content\)/);
assert.match(profile, /\.page\s*\{[^}]*background:\s*transparent/);
assert.match(
  profile,
  /\.user-card,[\s\S]*?\.panel\s*\{[\s\S]*?border:\s*1px solid var\(--app-card-border\)[\s\S]*?background:\s*var\(--app-panel-bg\)[\s\S]*?backdrop-filter:\s*blur\(var\(--app-blur\)\)[\s\S]*?box-shadow:\s*var\(--app-card-shadow\)/,
);
assert.match(
  profile,
  /nav\s*\{[\s\S]*?background:\s*var\(--app-panel-bg\)[\s\S]*?box-shadow:\s*var\(--app-card-shadow\)/,
);
assert.match(
  profile,
  /\.questionnaire-summary span\s*\{[\s\S]*?background:\s*var\(--app-control-bg\)[\s\S]*?backdrop-filter:\s*blur\(12px\)/,
);
assert.match(
  profile,
  /\.history-item\s*\{[\s\S]*?background:\s*var\(--app-control-bg\)[\s\S]*?backdrop-filter:\s*blur\(12px\)/,
);
for (const state of [emptyState, loadingState]) {
  assert.match(state, /background:\s*var\(--app-panel-soft-bg\)/);
  assert.match(state, /border:\s*1px dashed var\(--app-card-border\)/);
}
assert.doesNotMatch(
  profile,
  /(?:\.questionnaire-summary span|\.history-item|input)\s*\{[^}]*background:\s*#fff(?:fff)?/i,
);

assert.match(router, /function openProfileQuestionnaire\(to\)/);
assert.match(router, /return to\.hash \? true : profileQuestionnaireLocation/);
for (const legacyPath of [
  "/profile/recommend",
  "/profile/recommendation",
  "/profile/my-recommend",
  "/user/recommend",
  "/user/recommendation",
]) {
  assert.ok(router.includes(`"${legacyPath}"`), `${legacyPath} 应保留兼容跳转`);
}
assert.match(
  router,
  /const profileQuestionnaireLocation = \{\s*name: "Profile",\s*hash: "#questionnaire",\s*\}/,
);

assert.doesNotMatch(
  backend,
  /"profile": profile,\s*"recommendations": query_sites\(limit=6\)/,
);
assert.match(api, /export const careerAPI\s*=\s*\{/);
assert.match(api, /api\.get\("\/career\/recommend"/);
assert.match(home, /careerAPI\.getRecommendations/);
assert.match(home, /to="\/questionnaire"/);
assert.match(backend, /@app\.route\("\/api\/career\/recommendations"/);
assert.match(backend, /build_career_recommendations\(/);

console.log("PASS profile navigation and recommendation isolation checks");
