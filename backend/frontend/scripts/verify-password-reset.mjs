import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const read = (relativePath) =>
  readFileSync(new URL(relativePath, `file://${root.replaceAll("\\", "/")}/`), "utf8");

const login = read("src/views/Login.vue");
const forgot = read("src/views/ForgotPassword.vue");
const router = read("src/router/index.js");
const api = read("src/utils/api.js");

assert.match(login, /to="\/forgot-password"[\s\S]*忘记密码/);
assert.match(router, /path: "\/forgot-password"[\s\S]*ForgotPassword\.vue/);
assert.match(router, /name: "ForgotPassword"[\s\S]*meta: \{ public: true \}/);

assert.match(forgot, /v-model\.trim="email"/);
assert.match(forgot, /sendingCode[\s\S]*countdown > 0/);
assert.match(forgot, /countdown\.value = 60/);
assert.match(forgot, /v-model="code"[\s\S]*maxlength="6"/);
assert.match(forgot, /v-model="newPassword"/);
assert.match(forgot, /v-model="confirmPassword"/);
assert.match(forgot, /EyeOff[\s\S]*Eye/);
assert.match(forgot, /STRONG_PASSWORD_PATTERN/);
assert.match(forgot, /newPassword\.value !== confirmPassword\.value/);
assert.match(forgot, /authAPI\.sendPasswordResetCode/);
assert.match(forgot, /API_BASE_URL/);
assert.match(forgot, /console\.info\([\s\S]*\[password-reset\] send-code/);
assert.match(forgot, /test_code[\s\S]*\[REDACTED\]/);
assert.doesNotMatch(forgot, /errorToast/);
assert.match(
  forgot,
  /await authAPI\.sendPasswordResetCode\(value\)[\s\S]*startCountdown\(\)[\s\S]*} catch/,
);
assert.match(forgot, /authAPI\.resetPassword/);
assert.match(forgot, /confirm_password: confirmPassword\.value/);
assert.match(forgot, /router\.replace\(\{ path: "\/login", query: \{ reset: "success" \} \}\)/);
assert.match(forgot, /onBeforeUnmount\(clearTimer\)/);

assert.match(api, /"\/auth\/forgot-password\/send-code"/);
assert.match(api, /"\/auth\/forgot-password\/reset"/);
assert.doesNotMatch(api, /"\/auth\/(?:send-reset-code|verify-reset-code|reset-password)"/);

console.log("password reset frontend verification passed");
