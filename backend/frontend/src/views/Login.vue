<template>
  <div class="auth-page">
    <form class="auth-panel" @submit.prevent="submit">
      <RouterLink class="brand" to="/">智汇 AI 导航</RouterLink>
      <h1>登录账号</h1>
      <label>
        邮箱或用户名
        <input v-model.trim="account" autocomplete="username" required />
      </label>
      <label>
        密码
        <input
          v-model="password"
          autocomplete="current-password"
          type="password"
          required
        />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit" :disabled="loading">
        {{ loading ? "正在登录..." : "登录" }}
      </button>
      <RouterLink to="/register">还没有账号？去注册</RouterLink>
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
  background: #f8fafc;
  padding: 24px;
}
.auth-panel {
  display: grid;
  gap: 16px;
  width: min(420px, 100%);
  padding: 28px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}
.brand {
  color: #111827;
  font-weight: 850;
  text-decoration: none;
}
h1 {
  margin: 0;
}
label {
  display: grid;
  gap: 8px;
  color: #374151;
  font-weight: 700;
}
input {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 12px;
}
button {
  border: 0;
  border-radius: 8px;
  background: #111827;
  color: #fff;
  padding: 13px;
  font-weight: 800;
}
.error {
  margin: 0;
  color: #b91c1c;
}
</style>
