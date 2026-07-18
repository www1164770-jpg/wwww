<template>
  <div class="auth-page">
    <form class="auth-panel" @submit.prevent="submit">
      <RouterLink class="brand" to="/">智汇导航</RouterLink>
      <div class="auth-heading">
        <p>欢迎回来</p>
        <h1>登录账号</h1>
      </div>
      <label>
        邮箱或用户名
        <input
          v-model.trim="account"
          autocomplete="username"
          aria-label="邮箱或用户名"
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
          aria-label="密码"
          required
          @input="clearError"
        />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit" :disabled="loginLoading">
        {{ loginLoading ? "登录中..." : "登录" }}
      </button>
      <button type="button" class="authing-button" @click="loginWithAuthing">
        使用 Authing 登录
      </button>
      <RouterLink class="switch-link" to="/register">
        还没有账号？去注册
      </RouterLink>
    </form>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { API_BASE_URL, authAPI } from "../utils/api";
import { normalizeAuthSession } from "../utils/auth";
import { useUserStore } from "../stores/user";
import { errorToast, successToast } from "../utils/toast";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const account = ref("");
const password = ref("");
const loginLoading = ref(false);
const authingErrorMessages = {
  invalid_token: "登录凭证无效，请重新登录",
  jwt_failed: "生成登录凭证失败，请检查后端 JWT 配置。",
  state_mismatch: "登录状态校验失败，请重新登录",
  token_exchange_failed:
    "Authing 授权码换取 token 失败，请检查 App ID、App Secret 和回调地址",
  userinfo_failed: "获取 Authing 用户信息失败，请检查 Authing 应用配置。",
  user_sync_failed: "同步用户信息失败，请检查 users 表字段",
  authing_exchange_unavailable: "认证服务暂不可用，请稍后重试。",
  authing_failed: "Authing 登录失败，请稍后重试",
};
const error = ref(authingErrorMessages[route.query.authing_error] || "");

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
  if (error.value) {
    error.value = "";
  }
}

function showError(message) {
  error.value = message;
  errorToast(message);
}

async function submit() {
  if (loginLoading.value) return;
  if (!account.value.trim()) {
    showError("请输入邮箱或用户名");
    return;
  }
  if (!password.value) {
    showError("请输入密码");
    return;
  }
  loginLoading.value = true;
  error.value = "";
  try {
    const response = await authAPI.login(account.value, password.value);
    const session = normalizeAuthSession(response);
    const questionnaireCompleted = session.questionnaire_completed === true ||
      session.questionnaire_completed === 1 ||
      session.questionnaire_completed === "1" ||
      session.questionnaire_completed === "true";

    if (!session.access_token) {
      showError("登录成功但未返回登录凭证，请检查后端接口");
      return;
    }

    userStore.setLoginSuccess(session);
    successToast("登录成功");
    if (!questionnaireCompleted) {
      router.replace("/questionnaire");
    } else {
      router.replace(normalizeRedirect(route.query.redirect));
    }
  } catch (err) {
    if (err.response?.status === 429) {
      showError(err.response.data?.msg || "请求过于频繁，请稍后再试");
    } else if (err.response?.status === 401) {
      showError("账号或密码错误");
    } else {
      showError(err.response?.data?.msg || "账号或密码错误");
    }
  } finally {
    loginLoading.value = false;
  }
}

function loginWithAuthing() {
  const redirect = route.query.redirect || "/";
  const apiBase = API_BASE_URL;
  const backendBase = apiBase.replace(/\/api\/?$/, "");

  window.location.href = `${backendBase}/api/authing/login?redirect=${encodeURIComponent(
    redirect,
  )}`;
}
</script>

<style scoped>
.auth-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
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
  padding: 24px;
}

.auth-panel {
  display: grid;
  gap: 18px;
  width: min(460px, 100%);
  border: 1px solid var(--color-border);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  padding: clamp(28px, 5vw, 40px);
  box-shadow: var(--shadow-card);
}

.brand {
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
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: #ffffff;
  padding: 13px 14px;
}

button {
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--color-primary);
  color: #ffffff;
  padding: 14px;
  font-weight: 850;
  box-shadow: 0 14px 28px rgba(255, 112, 88, 0.18);
  transition:
    transform var(--transition),
    background var(--transition),
    box-shadow var(--transition);
}

button:hover,
button:focus-visible {
  background: var(--color-primary-dark);
  transform: translateY(-1px);
  box-shadow: 0 18px 34px rgba(255, 112, 88, 0.24);
  outline: none;
}

button:disabled {
  cursor: wait;
  opacity: 0.72;
}

.authing-button {
  border: 1px solid rgba(255, 112, 88, 0.34);
  background: #ffffff;
  color: var(--color-primary);
  box-shadow: none;
}

.authing-button:hover,
.authing-button:focus-visible {
  background: rgba(255, 112, 88, 0.08);
  color: var(--color-primary-dark);
  box-shadow: 0 14px 28px rgba(255, 112, 88, 0.12);
}

.switch-link {
  color: var(--color-primary);
  text-align: center;
  text-decoration: none;
  font-weight: 750;
}

.switch-link:hover,
.switch-link:focus-visible {
  color: var(--color-primary-dark);
  outline: none;
}

.error {
  margin: 0;
  color: #b91c1c;
  font-weight: 750;
}
</style>
