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
const auth = read("src/utils/auth.js");
const userStore = read("src/stores/user.js");
const authingCallback = read("src/views/AuthingCallback.vue");
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
expect(/import\s*\{\s*useUserStore\s*\}/.test(authingCallback), "Authing callback imports the user store");
expect(/const\s+userStore\s*=\s*useUserStore\(\)/.test(authingCallback), "Authing callback creates a user store instance");
expect(/const\s+session\s*=\s*normalizeAuthSession\(response\)/.test(authingCallback), "Authing callback normalizes the exchange response into a session");
expect(/userStore\.setLoginSuccess\(\s*session\s*\)/.test(authingCallback), "Authing callback passes the complete session to the user store");
expect(!/(?:localStorage|sessionStorage)\.setItem\s*\(/.test(authingCallback), "Authing callback does not write authentication storage directly");
expect(!/route\.query\.(?:access_token|token|refresh_token)\b/.test(authingCallback), "Authing callback does not read project JWTs from the URL");
expect(/function\s+setLoginSuccess\s*\([^)]*\)\s*\{[\s\S]*?saveAuthSession\(session\)/.test(userStore), "User store persists a complete login session through the shared auth utility");
expect(/accessToken:\s*"access_token"/.test(auth), "Shared auth utility defines the access token key");
expect(/refreshToken:\s*"refresh_token"/.test(auth), "Shared auth utility defines the refresh token key");
expect(/userInfo:\s*"user_info"/.test(auth), "Shared auth utility defines the user info key");
expect(/userRole:\s*"user_role"/.test(auth), "Shared auth utility defines the user role key");
expect(/questionnaireCompleted:\s*"questionnaire_completed"/.test(auth), "Shared auth utility defines the questionnaire completion key");
expect(/isLoggedIn:\s*"is_logged_in"/.test(auth), "Shared auth utility defines the login state key");
expect(/legacyToken:\s*"token"/.test(auth), "Shared auth utility retains the legacy token alias");
expect(/storage\.setItem\(AUTH_STORAGE_KEYS\.accessToken,\s*accessToken\)/.test(auth), "Shared auth utility stores the access token");
expect(/storage\.setItem\(AUTH_STORAGE_KEYS\.legacyToken,\s*accessToken\)/.test(auth), "Shared auth utility stores the legacy token alias");
expect(/storage\.setItem\(\s*AUTH_STORAGE_KEYS\.refreshToken/.test(auth), "Shared auth utility stores the refresh token");
expect(/storage\.setItem\(AUTH_STORAGE_KEYS\.userInfo,\s*serializedUser\)/.test(auth), "Shared auth utility stores user info");
expect(/storage\.setItem\(AUTH_STORAGE_KEYS\.userRole/.test(auth), "Shared auth utility stores the user role");
expect(/storage\.setItem\(\s*AUTH_STORAGE_KEYS\.questionnaireCompleted/.test(auth), "Shared auth utility stores questionnaire completion");
expect(/storage\.setItem\(AUTH_STORAGE_KEYS\.isLoggedIn,\s*"true"\)/.test(auth), "Shared auth utility stores login state");
expect(/router\.replace\(target\)/.test(authingCallback), "Authing callback keeps the success redirect");
expect(/catch\s*\(error\)\s*\{[\s\S]*?userStore\.logout\(\)[\s\S]*?router\.replace\(/.test(authingCallback), "Authing callback keeps logout and redirect error handling");
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
