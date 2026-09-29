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
const app = readFrontend("src/App.vue");
const router = readFrontend("src/router/index.js");
const home = readFrontend("src/views/Home.vue");
const api = readFrontend("src/utils/api.js");
const backend = readProject("backend/v1_routes.py");

const nav = profile.match(
  /<nav\s+class="profile-sidebar__nav"\s+aria-label="个人中心菜单">([\s\S]*?)<\/nav>/,
)?.[1];
assert.ok(nav, "个人中心菜单应存在");

for (const section of [
  "personalization",
  "survey",
  "favorites",
  "history",
  "password",
]) {
  assert.match(nav, new RegExp(`profileSectionLink\\('${section}'\\)`));
  assert.match(nav, new RegExp(`activeSection === '${section}'`));
}
assert.match(nav, /:to="\{ name: 'Profile' \}"/);
assert.doesNotMatch(nav, /to="\/personalization"/);
assert.match(profile, /<PersonalizationView[\s\S]*?embedded/);

assert.doesNotMatch(
  profile,
  /我的推荐|#recommendations|profile\.recommendations/,
);
assert.doesNotMatch(profile, /SiteList|function visit\(site\)/);
for (const id of ["questionnaire", "favorites", "history", "password"]) {
  assert.match(profile, new RegExp(`<section[^>]*id="${id}"`));
}
assert.match(
  profile,
  /\.profile-shell\s*\{[\s\S]*?grid-template-columns:\s*232px minmax\(0, 1fr\)/,
);
assert.match(app, /app-route-content--header-clearance/);
assert.match(
  app,
  /\.app-route-content--header-clearance\s*\{[\s\S]*?padding-top:\s*var\(--app-route-content-top\)/,
);
assert.match(
  app,
  /\.app-route-content--header-clearance > \.page\s*\{[\s\S]*?min-height:\s*calc\(100vh - var\(--app-route-content-top\)\)/,
);
assert.doesNotMatch(profile, /profile-header-clearance/);
assert.match(
  profile,
  /\.profile-page\s*\{[\s\S]*?background:\s*var\(--page-bg\)/,
);
assert.match(
  profile,
  /\.survey-grid\s*\{[\s\S]*?grid-template-columns:\s*repeat\(2, minmax\(0, 1fr\)\)/,
);
assert.match(
  profile,
  /\.survey-tags b\s*\{[\s\S]*?border-radius:\s*999px[\s\S]*?background:\s*var\(--surface-soft\)/,
);
assert.match(profile, /v-show="activeSection === 'personalization'"/);
assert.match(profile, /\.profile-section-panel\s*\{[\s\S]*?animation: profile-section-enter 200ms/);
assert.match(app, /\["Profile", "ProfileSection"\][\s\S]*?"profile-layout"/);
assert.match(profile, /<RouterLink class="profile-primary-link" to="\/favorites">/);
assert.match(profile, /<RouterLink class="profile-card__action" to="\/questionnaire">/);

assert.match(
  router,
  /path: "\/profile\/:section\(personalization\|survey\|favorites\|history\|password\)"/,
);
assert.match(router, /name: "ProfileSection"/);
assert.match(
  router,
  /path: "\/personalization",[\s\S]*?redirect: \{ name: "ProfileSection", params: \{ section: "personalization" \} \}/,
);
for (const legacyPath of [
  "/profile/recommend",
  "/profile/recommendation",
  "/profile/my-recommend",
  "/user/recommend",
  "/user/recommendation",
]) {
  assert.ok(router.includes(`"${legacyPath}"`), `${legacyPath} 应保留兼容跳转`);
}
assert.match(router, /params: \{ section: "survey" \}/);

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
