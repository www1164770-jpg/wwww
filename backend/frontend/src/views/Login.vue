<template>
  <div class="auth-page">
    <div class="left-dots" aria-hidden="true"></div>
    <div class="nautical-scene" aria-hidden="true">
      <div class="navigation-rings"></div>
      <svg class="lighthouse-art" viewBox="0 0 620 430" role="presentation">
        <defs>
          <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#b9d6f3" stop-opacity=".22" />
            <stop offset=".6" stop-color="#dcecff" stop-opacity=".16" />
            <stop offset="1" stop-color="#8fb9e3" stop-opacity=".04" />
          </linearGradient>
          <linearGradient id="mountain" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#b9cee5" stop-opacity=".18" />
            <stop offset="1" stop-color="#dce9f7" stop-opacity=".05" />
          </linearGradient>
          <linearGradient id="tower" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stop-color="#eaf4ff" />
            <stop offset=".55" stop-color="#fff" />
            <stop offset="1" stop-color="#b7cce5" />
          </linearGradient>
          <filter id="mist" x="-20%" y="-50%" width="140%" height="200%">
            <feGaussianBlur stdDeviation="12" />
          </filter>
        </defs>
        <path fill="url(#mountain)" d="M0 314c44-19 68-44 108-45 35 0 54 25 86 24 37-2 53-49 96-51 40-2 59 44 97 48 43 5 69-27 111-23 42 3 73 31 122 33v69H0z" />
        <path fill="#8fb0d2" fill-opacity=".08" d="M12 350c71-25 121-29 178-13 52 14 84-4 125-2 38 2 69 20 113 17 54-4 103-27 192-15v65H0z" />
        <path fill="url(#sea)" d="M0 353c111-13 185 7 276 3 113-4 188-25 344-9v83H0z" />
        <ellipse cx="278" cy="345" rx="255" ry="24" fill="#fff" fill-opacity=".44" filter="url(#mist)" />
        <g class="tower" transform="translate(-78 -60) scale(1.32)">
          <path fill="url(#tower)" d="m226 321 19-171h51l18 171z" />
          <path fill="#6f94bf" fill-opacity=".42" d="M245 150h51l-5 18h-44zM236 251h68l3 22h-74z" />
          <path fill="#173f70" fill-opacity=".72" d="M238 140h64v11h-64zM247 120h46l9 20h-64z" />
          <path fill="#ffd7a3" fill-opacity=".8" d="M252 125h35v15h-35z" />
          <path fill="#2d5d91" fill-opacity=".7" d="m270 99 5 21h-10z" />
          <rect x="266" y="196" width="9" height="24" rx="4" fill="#587da8" fill-opacity=".55" />
        </g>
        <g class="birds" fill="none" stroke="#6e96c2" stroke-linecap="round" stroke-width="1.5" opacity=".3">
          <path d="M346 174q12-13 24 0 12-13 24 0" />
          <path d="M397 135q9-10 18 0 9-10 18 0" />
        </g>
        <g fill="none" stroke="#fff" stroke-opacity=".38" stroke-width="2">
          <path d="M0 375q82-10 164 0t164 0 164 0 128 0" />
          <path d="M0 395q92-9 184 0t184 0 184 0" />
        </g>
      </svg>
    </div>
    <svg class="soft-waves" viewBox="0 0 760 260" aria-hidden="true">
      <path d="M0 176c156 1 184-82 338-80 151 2 193 76 422 9" />
      <path d="M0 210c163 1 221-73 364-68 143 4 190 57 396 4" />
      <path d="M74 242c145-2 216-58 350-54 111 4 176 35 336 5" />
    </svg>

    <form class="auth-panel" @submit.prevent="submit">
      <RouterLink class="brand" to="/">
        <svg class="brand-mark" viewBox="0 0 36 36" aria-hidden="true">
          <path class="brand-sail-light" d="M18 3 7 25h11z" />
          <path class="brand-sail-dark" d="m20 7 9 18h-9z" />
          <path class="brand-hull" d="M5 28c7 2 18 2 26 0-3 4-8 5-13 5S8 32 5 28Z" />
        </svg>
        <span>知航屿</span>
      </RouterLink>
      <div class="auth-heading">
        <p>欢迎回来</p>
        <h1>登录账号</h1>
      </div>
      <label class="field">
        <span class="field-label">邮箱或用户名</span>
        <span class="input-shell">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 6.5h16v11H4zM4.5 7l7.5 6 7.5-6" />
          </svg>
          <input
            v-model.trim="account"
            autocomplete="username"
            placeholder="请输入邮箱或用户名"
            required
            @input="clearError"
          />
        </span>
      </label>
      <label class="field">
        <span class="field-label">密码</span>
        <span class="input-shell">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 10h12v10H6zM8.5 10V7.5a3.5 3.5 0 0 1 7 0V10M12 14v2" />
          </svg>
          <input
            v-model="password"
            autocomplete="current-password"
            placeholder="请输入密码"
            :type="showPassword ? 'text' : 'password'"
            required
            @input="clearError"
          />
          <button
            class="password-toggle"
            type="button"
            :aria-label="showPassword ? '隐藏密码' : '显示密码'"
            :aria-pressed="showPassword"
            @click="showPassword = !showPassword"
          >
            <svg v-if="showPassword" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M2.5 12s3.5-5 9.5-5 9.5 5 9.5 5-3.5 5-9.5 5-9.5-5-9.5-5Z" />
              <circle cx="12" cy="12" r="2.5" />
            </svg>
            <svg v-else viewBox="0 0 24 24" aria-hidden="true">
              <path d="m4 4 16 16M10.6 7.2A9 9 0 0 1 12 7c6 0 9.5 5 9.5 5a15 15 0 0 1-3 3.2M6.3 6.8C3.9 8.3 2.5 12 2.5 12s3.5 5 9.5 5c1 0 2-.2 2.8-.4M9.9 9.9a3 3 0 0 0 4.2 4.2" />
            </svg>
          </button>
        </span>
      </label>
      <div class="password-meta">
        <RouterLink class="forgot-link" to="/forgot-password">
          忘记密码？
        </RouterLink>
      </div>
      <p v-if="route.query.reset === 'success'" class="success">
        密码重置成功，请使用新密码登录
      </p>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="login-button" type="submit" :disabled="loginLoading">
        {{ loginLoading ? "登录中…" : "登录" }}
      </button>
      <RouterLink class="switch-link" to="/register">
        <span>还没有账号？</span><strong>去注册</strong>
      </RouterLink>
    </form>

    <footer class="auth-footer">© 2026 知航屿 · 探索方向，抵达未来</footer>
  </div>
</template>

<script setup>
import axios from "axios";
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { authAPI } from "../utils/api";
import { normalizeAuthSession } from "../utils/auth";
import { useUserStore } from "../stores/user";
import { errorToast, successToast } from "../utils/toast";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const account = ref("");
const password = ref("");
const showPassword = ref(false);
const loginLoading = ref(false);
const error = ref("");

function normalizeRedirect(path) {
  const value = String(path || "");
  if (
    !value ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("\\") ||
    /[\u0000-\u001f]/.test(value)
  ) {
    return "/";
  }
  return value;
}

function clearError() {
  error.value = "";
}

function showError(message) {
  error.value = message;
  errorToast(message);
}

function getLoginErrorMessage(err) {
  const status = err?.response?.status;
  const responseData = err?.response?.data;
  const responseCode = responseData?.code;
  const serverMessage = responseData?.message ?? responseData?.msg;

  if (
    status === 401 ||
    responseCode === 401 ||
    responseCode === "INVALID_CREDENTIALS"
  ) {
    return "\u8d26\u53f7\u6216\u5bc6\u7801\u9519\u8bef";
  }
  if (status === 400)
    return serverMessage || "\u8bf7\u8f93\u5165\u90ae\u7bb1\u6216\u7528\u6237\u540d\u548c\u5bc6\u7801";
  if (status === 403 || responseCode === "ACCOUNT_DISABLED")
    return "\u8d26\u53f7\u4e0d\u53ef\u7528";
  if (status === 429)
    return "\u64cd\u4f5c\u8fc7\u4e8e\u9891\u7e41\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5";
  if (status === 503)
    return "\u6570\u636e\u5e93\u670d\u52a1\u6682\u65f6\u4e0d\u53ef\u7528\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5";
  if (status === 500)
    return "\u767b\u5f55\u670d\u52a1\u53d1\u751f\u5185\u90e8\u9519\u8bef";
  if (axios.isCancel(err) || err?.code === "ERR_CANCELED") {
    return "\u767b\u5f55\u8bf7\u6c42\u88ab\u53d6\u6d88\uff0c\u8bf7\u91cd\u65b0\u63d0\u4ea4";
  }
  if (
    err?.code === "ECONNABORTED" ||
    err?.code === "ETIMEDOUT" ||
    String(err?.message ?? "")
      .toLowerCase()
      .includes("timeout")
  ) {
    return "\u767b\u5f55\u8bf7\u6c42\u8d85\u65f6\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5";
  }
  if (err?.response) return serverMessage || "\u767b\u5f55\u5931\u8d25";
  return "\u65e0\u6cd5\u8fde\u63a5\u8ba4\u8bc1\u670d\u52a1";
}

async function submit() {
  if (loginLoading.value) return;
  if (!account.value.trim()) return showError("请输入邮箱或用户名");
  if (!password.value) return showError("请输入密码");

  loginLoading.value = true;
  error.value = "";
  try {
    const session = normalizeAuthSession(
      await authAPI.login(account.value.trim(), password.value),
    );
    if (!session.access_token) {
      showError("登录成功但未返回登录凭证，请检查后端接口");
      return;
    }

    userStore.setLoginSuccess(session);
    successToast("登录成功");
    await router.replace(normalizeRedirect(route.query.redirect));
  } catch (err) {
    if (import.meta.env.DEV) {
      console.error("[Auth] login error", {
        name: err?.name,
        message: err?.message,
        axiosCode: err?.code,
        status: err?.response?.status,
        responseCode: err?.response?.data?.code,
        responseMessage:
          err?.response?.data?.message ?? err?.response?.data?.msg,
        hasResponse: Boolean(err?.response),
        hasRequest: Boolean(err?.request),
        timeout: err?.config?.timeout,
        url: err?.config?.url,
        method: err?.config?.method,
        signalAborted: Boolean(err?.config?.signal?.aborted),
        isCanceled: axios.isCancel(err) || err?.code === "ERR_CANCELED",
        isTimeout:
          err?.code === "ECONNABORTED" ||
          err?.code === "ETIMEDOUT" ||
          String(err?.message ?? "")
            .toLowerCase()
            .includes("timeout"),
      });
    }
    showError(getLoginErrorMessage(err));
    return;
  } finally {
    loginLoading.value = false;
  }
}
</script>

<style scoped>
:global(html:has(.auth-page)),
:global(body:has(.auth-page)) {
  height: 100%;
  overflow: hidden;
}

.auth-page {
  --auth-navy: #102a4c;
  --auth-blue: #2563eb;
  --space-xs: 8px;
  --space-sm: 12px;
  --space-md: 20px;
  --space-lg: 28px;
  --space-xl: 38px;

  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100vh;
  min-height: 100dvh;
  overflow: hidden;
  padding: 0;
  background:
    radial-gradient(circle at 16% 18%, rgba(219, 234, 254, 0.75), transparent 34%),
    radial-gradient(circle at 84% 18%, rgba(254, 226, 226, 0.55), transparent 34%),
    linear-gradient(110deg, #f7fbff 0%, #ffffff 50%, #fff8f7 100%);
  isolation: isolate;
}

.auth-page::before {
  position: absolute;
  z-index: -1;
  top: 16%;
  left: 79%;
  width: clamp(100px, 11vw, 180px);
  aspect-ratio: 1;
  border-radius: 50%;
  background: radial-gradient(
    circle at 35% 35%,
    rgba(255, 255, 255, 0.25),
    rgba(252, 165, 165, 0.3)
  );
  filter: blur(0.2px);
  opacity: 0.65;
  content: "";
}

.auth-page::after {
  position: absolute;
  z-index: -1;
  top: 31%;
  left: 83%;
  width: 110px;
  height: 90px;
  background-image: radial-gradient(circle, rgba(226, 124, 124, 0.16) 2px, transparent 2.5px);
  background-size: 20px 20px;
  opacity: 0.55;
  content: "";
}

.left-dots {
  position: absolute;
  z-index: -1;
  top: 20%;
  left: 22%;
  width: 72px;
  height: 128px;
  background-image: radial-gradient(circle, rgba(116, 153, 195, 0.35) 1.5px, transparent 2px);
  background-size: 18px 18px;
  opacity: 0.15;
}

.soft-waves {
  position: absolute;
  z-index: -1;
  right: -2%;
  bottom: -1%;
  width: min(42vw, 780px);
  height: auto;
  fill: none;
  stroke: #d9aeb5;
  stroke-width: 1.2;
  opacity: 0.12;
  pointer-events: none;
}

.nautical-scene {
  position: absolute;
  z-index: -1;
  bottom: 7vh;
  left: 2vw;
  width: min(34vw, 580px);
  height: min(45vh, 480px);
  opacity: 0.52;
  pointer-events: none;
}

.navigation-rings {
  position: absolute;
  bottom: 2%;
  left: -4%;
  width: min(29vw, 480px);
  aspect-ratio: 1;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 50%;
  background:
    linear-gradient(90deg, transparent 49.8%, rgba(255,255,255,.28) 50%, transparent 50.2%),
    linear-gradient(transparent 49.8%, rgba(255,255,255,.28) 50%, transparent 50.2%);
  box-shadow:
    inset 0 0 0 46px transparent,
    0 0 0 46px rgba(255, 255, 255, 0.08),
    0 0 0 47px rgba(255, 255, 255, 0.14);
  opacity: 0.45;
}

.lighthouse-art {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: auto;
  opacity: 0.7;
}

.auth-panel {
  --auth-text-primary: #1e293b;
  --auth-text-secondary: #64748b;
  --auth-text-muted: #94a3b8;
  --auth-input-text: #1f2937;
  --auth-input-placeholder: #94a3b8;
  --auth-input-border: #dce3ec;
  --auth-input-background: rgba(255, 255, 255, 0.72);
  --auth-panel-background: rgba(255, 255, 255, 0.76);
  --auth-link-text: #2563eb;
  --auth-link-hover: #1d4ed8;

  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  width: clamp(520px, 32vw, 620px);
  height: auto;
  max-width: calc(100vw - 48px);
  padding: clamp(38px, 4vh, 48px) clamp(42px, 3vw, 54px);
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: 26px;
  color: var(--auth-text-secondary);
  background: var(--auth-panel-background);
  box-shadow:
    0 24px 55px rgba(15, 23, 42, 0.1),
    0 6px 16px rgba(15, 23, 42, 0.045);
  position: absolute;
  top: clamp(56px, 10vh, 110px);
  transform: none;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
}

:global(html[data-theme="dark"]) .auth-panel,
:global(html[data-color-scheme="dark"]) .auth-panel,
:global(html.dark) .auth-panel {
  --auth-text-primary: #f8fafc;
  --auth-text-secondary: #cbd5e1;
  --auth-text-muted: #94a3b8;
  --auth-input-text: #f8fafc;
  --auth-input-placeholder: #94a3b8;
  --auth-input-border: rgba(255, 255, 255, 0.14);
  --auth-input-background: rgba(15, 23, 42, 0.72);
  --auth-panel-background: rgba(15, 23, 42, 0.88);
  --auth-link-text: #93c5fd;
  --auth-link-hover: #bfdbfe;
  --auth-navy: #f8fafc;
}

.brand {
  display: inline-flex;
  width: fit-content;
  min-height: 36px;
  align-items: center;
  gap: 10px;
  color: var(--auth-text-primary);
  -webkit-text-fill-color: currentColor;
  font-size: 20px;
  font-weight: 700;
  text-decoration: none;
}

.brand-mark {
  width: 32px;
  height: 32px;
}

.brand-sail-light {
  fill: #6aa2dd;
}

.brand-sail-dark,
.brand-hull {
  fill: #153f72;
}

.switch-link,
.forgot-link {
  color: var(--auth-link-text);
  -webkit-text-fill-color: currentColor;
  text-decoration: none;
}

.switch-link:hover,
.switch-link:focus-visible,
.forgot-link:hover,
.forgot-link:focus-visible {
  color: var(--auth-link-hover);
  -webkit-text-fill-color: currentColor;
}

.password-meta {
  display: flex;
  justify-content: flex-end;
  margin-top: -12px;
}

.forgot-link {
  font-size: 14px;
  font-weight: 600;
}

.auth-heading {
  margin: 0;
}

.auth-heading p {
  margin: 0 0 6px;
  color: var(--auth-text-secondary);
  -webkit-text-fill-color: var(--auth-text-secondary);
  font-size: 16px;
  font-weight: 500;
}

h1 {
  margin: 0;
  color: var(--auth-navy);
  -webkit-text-fill-color: var(--auth-navy);
  font-size: 34px;
  font-weight: 700;
  letter-spacing: -0.5px;
  line-height: 1.2;
}

.field {
  display: grid;
  gap: 8px;
}

.field-label {
  color: var(--auth-text-primary);
  -webkit-text-fill-color: var(--auth-text-primary);
  font-size: 14px;
  font-weight: 600;
}

.input-shell {
  position: relative;
  display: flex;
  height: 52px;
  align-items: center;
}

.input-shell > svg {
  position: absolute;
  z-index: 1;
  left: 15px;
  width: 19px;
  height: 19px;
  fill: none;
  stroke: var(--auth-text-secondary);
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.7;
  pointer-events: none;
}

.password-toggle {
  position: absolute;
  z-index: 2;
  right: 9px;
  display: grid;
  width: 36px;
  min-width: 36px;
  height: 36px;
  min-height: 36px;
  padding: 8px;
  place-items: center;
  border: 0;
  border-radius: 50%;
  color: var(--auth-text-secondary);
  background: transparent;
}

.password-toggle:hover,
.password-toggle:focus-visible {
  color: var(--auth-navy);
  background: rgba(37, 99, 235, 0.06);
  outline: none;
}

.password-toggle svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 1.7;
}

input {
  width: 100%;
  height: 52px;
  min-width: 0;
  padding: 0 16px 0 45px;
  border: 1px solid var(--auth-input-border);
  border-radius: 12px;
  color: var(--auth-input-text);
  -webkit-text-fill-color: var(--auth-input-text);
  caret-color: var(--auth-input-text);
  background: var(--auth-input-background);
  opacity: 1;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    background-color 0.2s ease;
}

.field:last-of-type input {
  padding-right: 50px;
}

input::placeholder {
  color: var(--auth-input-placeholder);
  -webkit-text-fill-color: var(--auth-input-placeholder);
  opacity: 1;
}

input:hover:not(:disabled) {
  color: var(--auth-input-text);
  -webkit-text-fill-color: var(--auth-input-text);
  border-color: #b8c6d8;
}

input:focus {
  color: var(--auth-input-text);
  -webkit-text-fill-color: var(--auth-input-text);
  border-color: #7aa7df !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.08);
}

input:disabled {
  color: var(--auth-text-muted);
  -webkit-text-fill-color: var(--auth-text-muted);
  background: color-mix(
    in srgb,
    var(--auth-input-background) 88%,
    var(--auth-text-muted)
  );
  opacity: 1;
}

input:-webkit-autofill,
input:-webkit-autofill:hover,
input:-webkit-autofill:focus,
input:-webkit-autofill:active {
  -webkit-text-fill-color: var(--auth-input-text);
  caret-color: var(--auth-input-text);
  box-shadow: 0 0 0 1000px var(--auth-input-background) inset;
  transition: background-color 9999s ease-out 0s;
}

.login-button {
  height: 54px;
  margin-top: 2px;
  margin-bottom: 2px;
  padding: 0 18px;
  border: 0;
  border-radius: 999px;
  background: linear-gradient(100deg, #20569a 0%, #173d70 45%, #0f294b 100%);
  color: #ffffff;
  -webkit-text-fill-color: #ffffff;
  font-size: 16px;
  font-weight: 700;
  box-shadow:
    -5px 0 20px rgba(37, 99, 235, 0.16),
    0 8px 20px rgba(15, 41, 75, 0.14);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    filter 0.2s ease;
}

.login-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(30, 76, 134, 0.2);
  filter: brightness(1.04);
}

.login-button:active:not(:disabled) {
  transform: translateY(0);
}

.login-button:disabled {
  color: #ffffff;
  -webkit-text-fill-color: #ffffff;
  cursor: wait;
  opacity: 0.68;
}

.switch-link {
  display: flex;
  min-height: 30px;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 0;
  text-align: center;
}

.switch-link span {
  color: var(--auth-text-secondary);
  -webkit-text-fill-color: var(--auth-text-secondary);
}

.switch-link strong {
  color: var(--auth-link-text);
  -webkit-text-fill-color: var(--auth-link-text);
  font-weight: 600;
}

.error {
  margin: 0;
  padding: 9px 12px;
  border-radius: 8px;
  color: #b91c1c;
  background: rgba(254, 226, 226, 0.65);
  font-size: 13px;
  font-weight: 600;
}

.success {
  margin: 0;
  padding: 9px 12px;
  border-radius: 8px;
  color: #15803d;
  background: rgba(220, 252, 231, 0.66);
  font-size: 13px;
  font-weight: 600;
}

.auth-footer {
  position: absolute;
  bottom: 22px;
  left: 50%;
  width: max-content;
  max-width: calc(100% - 32px);
  transform: translateX(-50%);
  color: #8493a7;
  font-size: 12px;
  text-align: center;
}

@media (max-width: 1024px) {
  .auth-panel {
    width: min(540px, calc(100vw - 48px));
  }

  .nautical-scene {
    width: 40vw;
    opacity: 0.42;
  }
}

@media (max-width: 768px) {
  .auth-page {
    min-height: 100dvh;
    padding: 24px 16px 52px;
  }

  .auth-panel {
    width: calc(100% - 32px);
    max-width: 500px;
    position: relative;
    top: auto;
    height: auto;
    max-height: calc(100dvh - 76px);
    padding: 28px 32px;
    gap: 14px;
    overflow-y: auto;
    transform: none;
  }

  .nautical-scene,
  .left-dots,
  .soft-waves,
  .auth-page::before,
  .auth-page::after {
    display: none;
  }

  .auth-heading {
    margin-top: 2px;
    margin-bottom: 2px;
  }

  .switch-link {
    margin-top: 2px;
  }
}

@media (max-width: 480px) {
  .auth-page {
    align-items: center;
    padding-inline: 16px;
  }

  .auth-panel {
    width: 100%;
    padding: 28px 24px;
    border-radius: 22px;
  }

  .auth-heading {
    margin-top: 2px;
  }

  h1 {
    font-size: 30px;
  }

  .auth-footer {
    bottom: 16px;
  }
}

@media (max-height: 800px) and (min-width: 769px) {
  .auth-panel {
    top: clamp(40px, 7vh, 56px);
    min-height: 0;
    gap: 12px;
    padding-block: 24px;
    transform: none;
  }

  .auth-heading {
    margin-top: 0;
    margin-bottom: 0;
  }

}
</style>
