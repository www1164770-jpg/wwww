<template>
  <div class="auth-page">
    <form class="auth-panel" @submit.prevent="submit">
      <RouterLink class="brand" to="/">知航屿</RouterLink>
      <div class="auth-heading">
        <p>欢迎回来</p>
        <h1>登录账号</h1>
      </div>
      <label>
        邮箱或用户名
        <input
          v-model.trim="account"
          autocomplete="username"
          required
          @input="clearError"
        />
      </label>
      <label>
        密码
        <input
          v-model="password"
          autocomplete="current-password"
          type="password"
          required
          @input="clearError"
        />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit" :disabled="loginLoading">
        {{ loginLoading ? "登录中…" : "登录" }}
      </button>
      <RouterLink class="switch-link" to="/register">
        还没有账号？去注册
      </RouterLink>
    </form>
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
  if (status >= 500)
    return "\u767b\u5f55\u670d\u52a1\u6682\u65f6\u4e0d\u53ef\u7528";
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
.auth-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(
      circle at 12% 20%,
      rgba(191, 245, 237, 0.42),
      transparent 28%
    ),
    radial-gradient(
      circle at 90% 30%,
      rgba(255, 112, 88, 0.16),
      transparent 30%
    ),
    linear-gradient(180deg, #ffffff 0%, #fffaf8 100%);
}

.auth-panel {
  display: grid;
  gap: 18px;
  width: min(460px, 100%);
  padding: clamp(28px, 5vw, 40px);
  border: 1px solid var(--color-border);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--shadow-card);
}

.brand,
.switch-link {
  color: var(--color-primary);
  font-weight: 850;
  text-decoration: none;
}

.auth-heading p {
  margin: 0 0 6px;
  color: #718096;
  font-weight: 750;
}

h1 {
  margin: 0;
  color: var(--color-heading);
  font-size: 34px;
}

label {
  display: grid;
  gap: 8px;
  color: var(--color-heading);
  font-weight: 750;
}

input {
  min-width: 0;
  padding: 13px 14px;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: #ffffff;
}

button {
  padding: 14px;
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--color-primary);
  color: #ffffff;
  font-weight: 850;
  box-shadow: 0 14px 28px rgba(255, 112, 88, 0.18);
}

button:disabled {
  cursor: wait;
  opacity: 0.72;
}

.switch-link {
  text-align: center;
}

.error {
  margin: 0;
  color: #b91c1c;
  font-weight: 750;
}
</style>
