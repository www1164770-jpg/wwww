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
        />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit" :disabled="loading">
        {{ loading ? "正在登录..." : "登录" }}
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
import { authAPI } from "../utils/api";

const route = useRoute();
const router = useRouter();
const account = ref("");
const password = ref("");
const loading = ref(false);
const error = ref("");

function dataOf(response) {
  return response?.data?.data ?? response?.data ?? {};
}

async function submit() {
  loading.value = true;
  error.value = "";
  try {
    const response = await authAPI.login(account.value, password.value);
    const data = dataOf(response);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token || "");
    localStorage.setItem("user_info", JSON.stringify(data.user_info || {}));
    localStorage.setItem("user_role", data.user_role || "user");
    localStorage.setItem(
      "questionnaire_completed",
      String(Boolean(data.questionnaire_completed)),
    );
    localStorage.setItem("is_logged_in", "true");
    if (!data.questionnaire_completed) {
      router.push("/questionnaire");
    } else {
      router.push(route.query.redirect || "/");
    }
  } catch (err) {
    error.value = err.response?.data?.msg || "登录失败，请检查账号和密码";
  } finally {
    loading.value = false;
  }
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
