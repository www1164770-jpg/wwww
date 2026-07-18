import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";

import {
  AUTH_STORAGE_KEYS,
  applyAuthRequestHeaders,
  clearAuthSession,
  getAccessToken,
  isValidAuthToken,
  normalizeAuthSession,
  saveAuthSession,
} from "../src/utils/auth.js";

class MemoryStorage {
  #values = new Map();

  getItem(key) {
    return this.#values.has(key) ? this.#values.get(key) : null;
  }

  setItem(key, value) {
    this.#values.set(String(key), String(value));
  }

  removeItem(key) {
    this.#values.delete(String(key));
  }
}

global.localStorage = new MemoryStorage();
global.window = { dispatchEvent() {} };

const accessToken = "header.payload.signature";
const refreshToken = "refresh.header.signature";
const session = normalizeAuthSession({
  access_token: accessToken,
  refresh_token: refreshToken,
  user_info: {
    id: 1,
    username: "alice",
    email: "alice@example.com",
    avatar: "https://example.com/avatar.png",
  },
  user_role: "user",
  questionnaire_completed: false,
});

saveAuthSession(session);

assert.equal(localStorage.getItem(AUTH_STORAGE_KEYS.accessToken), accessToken);

const apiSource = readFileSync(
  fileURLToPath(new URL("../src/utils/api.js", import.meta.url)),
  "utf8",
);
assert.match(apiSource, /let refreshPromise = null/);
assert.match(apiSource, /originalConfig\._retry = true/);
assert.match(apiSource, /skipAuth: true/);
assert.match(apiSource, /\/auth\/refresh/);
assert.match(
  apiSource,
  /api\.interceptors\.request\.use\(applyAuthRequestHeaders\)/,
);
assert.match(apiSource, /Authorization: `Bearer \$\{refreshToken\}`/);
assert.doesNotMatch(
  apiSource,
  /if \(config\.skipAuth\)[\s\S]{0,160}delete config\.headers\.Authorization/,
);
assert.equal(localStorage.getItem(AUTH_STORAGE_KEYS.legacyToken), accessToken);
assert.equal(
  localStorage.getItem(AUTH_STORAGE_KEYS.refreshToken),
  refreshToken,
);
assert.equal(
  localStorage.getItem(AUTH_STORAGE_KEYS.userInfo),
  JSON.stringify(session.user_info),
);
assert.equal(
  localStorage.getItem(AUTH_STORAGE_KEYS.user),
  JSON.stringify(session.user_info),
);
assert.equal(localStorage.getItem(AUTH_STORAGE_KEYS.userRole), "user");
assert.equal(
  localStorage.getItem(AUTH_STORAGE_KEYS.questionnaireCompleted),
  "false",
);
assert.equal(localStorage.getItem(AUTH_STORAGE_KEYS.isLoggedIn), "true");

const refreshRequest = applyAuthRequestHeaders({
  skipAuth: true,
  headers: { Authorization: `Bearer ${refreshToken}` },
});
assert.equal(refreshRequest.headers.Authorization, `Bearer ${refreshToken}`);

const ordinaryRequest = applyAuthRequestHeaders({ headers: {} });
assert.equal(ordinaryRequest.headers.Authorization, `Bearer ${accessToken}`);

const unauthenticatedRequest = applyAuthRequestHeaders({
  skipAuth: true,
  headers: {},
});
assert.equal(unauthenticatedRequest.headers.Authorization, undefined);

clearAuthSession();
for (const key of Object.values(AUTH_STORAGE_KEYS)) {
  assert.equal(localStorage.getItem(key), null, `${key} should be cleared`);
}

localStorage.setItem(AUTH_STORAGE_KEYS.legacyToken, accessToken);
assert.equal(getAccessToken(), accessToken);
assert.equal(localStorage.getItem(AUTH_STORAGE_KEYS.accessToken), accessToken);

const authingCallbackSource = readFileSync(
  fileURLToPath(new URL("../src/views/AuthingCallback.vue", import.meta.url)),
  "utf8",
);
const scriptSetupMatch = authingCallbackSource.match(
  /<script setup>([\s\S]*?)<\/script>/,
);
assert.ok(
  scriptSetupMatch,
  "AuthingCallback.vue should contain a script setup block",
);
const executableAuthingCallback = scriptSetupMatch[1].replace(
  /^import .*;\r?\n/gm,
  "",
);

async function runAuthingCallback({
  questionnaireCompleted,
  redirect,
  exchangeError,
}) {
  let mountedCallback;
  let logoutCount = 0;
  const redirects = [];
  const loginSessions = [];
  const response = {
    data: {
      data: {
        access_token: accessToken,
        refresh_token: refreshToken,
        user_info: {
          id: 1,
          username: "authing-user",
          email: "authing-user@example.com",
          avatar: "https://example.com/authing-avatar.png",
        },
        user_role: "user",
        questionnaire_completed: questionnaireCompleted,
        redirect,
      },
    },
  };

  runInNewContext(
    executableAuthingCallback,
    {
      authAPI: {
        async exchange(code) {
          assert.equal(code, "one-time-code");
          if (exchangeError) throw exchangeError;
          return response;
        },
      },
      console,
      isValidAuthToken,
      normalizeAuthSession,
      onMounted(callback) {
        mountedCallback = callback;
      },
      useRoute() {
        return { query: { code: "one-time-code" } };
      },
      useRouter() {
        return {
          replace(target) {
            redirects.push(target);
          },
        };
      },
      useUserStore() {
        return {
          logout() {
            logoutCount += 1;
          },
          setLoginSuccess(authSession) {
            loginSessions.push(authSession);
          },
        };
      },
    },
    { filename: "AuthingCallback.vue" },
  );

  assert.equal(typeof mountedCallback, "function");
  await mountedCallback();
  return { loginSessions, logoutCount, redirects };
}

for (const [redirect, expected] of [
  ["/", "/"],
  ["/favorites", "/favorites"],
]) {
  const result = await runAuthingCallback({
    questionnaireCompleted: true,
    redirect,
  });
  assert.deepEqual(result.redirects, [expected]);
  assert.equal(result.loginSessions.length, 1);
  assert.equal(result.logoutCount, 0);
}

for (const redirect of ["/", "/favorites", "https://evil.example"]) {
  const result = await runAuthingCallback({
    questionnaireCompleted: false,
    redirect,
  });
  assert.deepEqual(result.redirects, ["/questionnaire"]);
}

for (const dangerousRedirect of [
  "https://evil.example",
  "//evil.example",
  "/\\evil.example",
  "javascript:alert(1)",
  "data:text/html,evil",
]) {
  const result = await runAuthingCallback({
    questionnaireCompleted: true,
    redirect: dangerousRedirect,
  });
  assert.deepEqual(result.redirects, ["/"]);
}

const exchangeError = new Error("exchange unavailable");
exchangeError.response = { status: 503 };
const failedExchange = await runAuthingCallback({
  questionnaireCompleted: true,
  redirect: "/favorites",
  exchangeError,
});
assert.deepEqual(failedExchange.redirects, [
  "/login?authing_error=authing_exchange_unavailable",
]);
assert.equal(failedExchange.loginSessions.length, 0);
assert.equal(failedExchange.logoutCount, 1);

console.log("auth state smoke test passed");
