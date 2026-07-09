import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const checks = [];

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), "utf8");
}

function exists(relativePath) {
  return fs.existsSync(path.join(root, relativePath));
}

function expect(condition, message) {
  checks.push({ ok: Boolean(condition), message });
}

const router = read("src/router/index.js");
const api = read("src/utils/api.js");
const v1Routes = read("../v1_routes.py");

for (const route of [
  "/admin/questionnaires",
  "/admin/recommend-rules",
  "/admin/settings",
]) {
  expect(router.includes(route), `router includes ${route}`);
}

for (const page of [
  "src/views/admin/AdminQuestionnaires.vue",
  "src/views/admin/AdminRecommendRules.vue",
  "src/views/admin/AdminSettings.vue",
]) {
  expect(exists(page), `${page} exists`);
}

for (const helper of [
  "getQuestionnaires",
  "saveQuestionnaireConfig",
  "getRecommendRules",
  "saveRecommendRules",
  "getSettings",
  "saveSettings",
]) {
  expect(api.includes(helper), `adminAPI exposes ${helper}`);
}

for (const endpoint of [
  "/api/admin/questionnaires",
  "/api/admin/recommend-rules",
  "/api/admin/settings",
]) {
  expect(v1Routes.includes(endpoint), `backend exposes ${endpoint}`);
}

expect(exists("REQUIREMENT_CHECKLIST.md"), "REQUIREMENT_CHECKLIST.md exists");
expect(exists("FRONTEND_CHECKLIST.md"), "FRONTEND_CHECKLIST.md exists");
expect(v1Routes.includes('"message": msg'), "api_success includes message");
expect(v1Routes.includes('"code": code'), "api_error includes code");
expect(v1Routes.includes('setting_value LONGTEXT NOT NULL'), "settings storage avoids JSON-only table dependency");
expect(v1Routes.includes('load_json_setting("recommend_rules"'), "recommend endpoint loads saved rules");
expect(v1Routes.includes("rank_sites(source_sites, profile, limit, rules"), "recommend endpoint passes rules to ranking");
expect(api.includes("storeUserSessionFromPayload"), "api exposes shared user session helper");
expect(read("src/views/AuthingCallback.vue").includes("storeUserSessionFromPayload"), "Authing callback stores fetched user info");
expect(!exists("backend/frontend/src/views/AuthingCallback.vue"), "no nested accidental Authing callback file");

const failed = checks.filter((check) => !check.ok);
if (failed.length) {
  for (const check of failed) {
    console.error(`FAIL ${check.message}`);
  }
  process.exit(1);
}

for (const check of checks) {
  console.log(`PASS ${check.message}`);
}
