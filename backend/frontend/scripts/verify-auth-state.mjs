import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const read = (relativePath) =>
  readFileSync(
    new URL(relativePath, `file://${root.replaceAll("\\", "/")}/`),
    "utf8",
  );

const register = read("src/views/Register.vue");
const login = read("src/views/Login.vue");
const router = read("src/router/index.js");
const api = read("src/utils/api.js");
const packageJson = JSON.parse(read("package.json"));
const legacyAuthMarker = ["auth", "ing"].join("");

assert.match(register, /verificationCode/);
assert.match(register, /sendVerificationCode/);
assert.match(register, /authAPI\.sendRegisterCode/);
assert.match(register, /verification_code/);
assert.match(register, /MAIL_CONNECTION_FAILED/);
assert.doesNotMatch(
  login,
  new RegExp(`${legacyAuthMarker}|Guard|callback`, "i"),
);
assert.doesNotMatch(router, new RegExp(`${legacyAuthMarker}|callback`, "i"));
assert.doesNotMatch(api, new RegExp(`${legacyAuthMarker}|send-code`, "i"));
assert.match(api, /send-register-code/);
assert.equal(
  existsSync(
    new URL(
      `src/views/${legacyAuthMarker}Callback.vue`,
      `file://${root.replaceAll("\\", "/")}/`,
    ),
  ),
  false,
);
assert.equal(
  Object.keys(packageJson.dependencies || {}).some((name) =>
    new RegExp(legacyAuthMarker, "i").test(name),
  ),
  false,
);
assert.match(
  register,
  /authAPI\.register\(\{[\s\S]*username[\s\S]*email[\s\S]*password/,
);
assert.match(login, /authAPI\.login\(/);
assert.match(api, /clearAuthSession\(\)/);

console.log("local auth smoke test passed");
