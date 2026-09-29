import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { loadEnv } from "vite";
import { resolveApiBaseURL } from "../src/utils/apiBase.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const read = (relativePath) =>
  readFileSync(new URL(relativePath, `file://${root.replaceAll("\\", "/")}/`), "utf8");

const api = read("src/utils/api.js");
const login = read("src/views/Login.vue");
const register = read("src/views/Register.vue");
// Vite permits no .env.development; verify the effective API base, including fallback.
const env = loadEnv("development", root);

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
assert.match(login, /status === 400/);
assert.match(login, /status === 403/);
assert.match(login, /status === 429/);
assert.match(login, /status === 503/);
assert.match(login, /status === 500/);
assert.doesNotMatch(login, /status >= 500[\s\S]{0,120}暂时不可用/);
assert.match(login, /ERR_CANCELED/);
assert.match(login, /ECONNABORTED/);
assert.match(login, /hasResponse: Boolean\(err\?\.response\)/);
assert.match(login, /signalAborted: Boolean\(err\?\.config\?\.signal\?\.aborted\)/);
assert.doesNotMatch(login, /console\.(debug|error)\([^\n]*(?:password|account)\b/i);
assert.match(register, /verification_code/);
const previousProxy = process.env.API_PROXY_TARGET;
try {
  delete process.env.API_PROXY_TARGET;
  const local = (await import('../vite.config.js?auth-contract-local')).default;
  assert.equal(local.server.proxy['/api'].target, 'http://127.0.0.1:5000');
  assert.equal(local.server.proxy['/api'].changeOrigin, true);
  process.env.API_PROXY_TARGET = 'http://isolated-backend.invalid:5000';
  const configured = (await import('../vite.config.js?auth-contract-configured')).default;
  assert.equal(configured.server.proxy['/api'].target, process.env.API_PROXY_TARGET);
} finally {
  if (previousProxy === undefined) delete process.env.API_PROXY_TARGET;
  else process.env.API_PROXY_TARGET = previousProxy;
}
assert.equal(resolveApiBaseURL(env, "/api"), "/api");

console.log("auth request contract verification passed");
