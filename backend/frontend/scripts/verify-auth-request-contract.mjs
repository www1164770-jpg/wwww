import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const read = (relativePath) =>
  readFileSync(new URL(relativePath, `file://${root.replaceAll("\\", "/")}/`), "utf8");

const api = read("src/utils/api.js");
const login = read("src/views/Login.vue");
const register = read("src/views/Register.vue");
const vite = read("vite.config.js");
const env = read(".env.development");

assert.match(api, /const DEFAULT_API_BASE_URL = "\/api"/);
assert.match(api, /timeout: API_TIMEOUT_MS/);
assert.match(api, /export const API_TIMEOUT_MS = 15000/);
assert.match(api, /withCredentials: true/);
assert.match(api, /timeout: AUTH_REQUEST_TIMEOUT_MS/);
assert.match(api, /export const AUTH_REQUEST_TIMEOUT_MS = 15000/);
assert.match(api, /export const VERIFICATION_REQUEST_TIMEOUT_MS = 30000/);
assert.match(api, /"\/auth\/login"[\s\S]*\{ account: account\.trim\(\), password \}/);
assert.match(api, /"\/auth\/register"[\s\S]*AUTH_REQUEST_TIMEOUT_MS/);
assert.match(api, /"\/auth\/send-register-code"[\s\S]*VERIFICATION_REQUEST_TIMEOUT_MS/);
assert.doesNotMatch(api, /AbortController|controller\.abort|CancelToken|Promise\.race/);
assert.match(login, /status === 401/);
assert.match(login, /ERR_CANCELED/);
assert.match(login, /ECONNABORTED/);
assert.match(login, /hasResponse: Boolean\(err\?\.response\)/);
assert.match(login, /signalAborted: Boolean\(err\?\.config\?\.signal\?\.aborted\)/);
assert.doesNotMatch(login, /console\.(debug|error)[\s\S]*password/);
assert.match(register, /verification_code/);
assert.match(vite, /['"]\/api['"][\s\S]*target: ['"]http:\/\/127\.0\.0\.1:5000/);
assert.match(env, /^VITE_API_BASE_URL=\/api$/m);

console.log("auth request contract verification passed");
