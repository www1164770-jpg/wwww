<template>
  <div class="auth-page">
    <form class="auth-panel" @submit.prevent="submit">
      <RouterLink class="brand" to="/">智慧导航</RouterLink>
      <div>
        <p>开启个性化推荐</p>
        <h1>注册账号</h1>
      </div>
      <label>用户名<input v-model.trim="form.username" required /></label>
      <label
        >邮箱<input v-model.trim="form.email" type="email" required
      /></label>
      <label
        >密码<input v-model="form.password" type="password" required
      /></label>
      <label>
        确认密码
        <input v-model="confirmPassword" type="password" required />
      </label>
      <div class="code-row">
        <label>邮箱验证码<input v-model.trim="form.code" required /></label>
        <button type="button" class="secondary" @click="sendCode">
          发送验证码
        </button>
      </div>
      <label class="check">
        <input v-model="accepted" type="checkbox" />
        我已阅读并同意用户协议和隐私政策
      </label>
      <p v-if="message" :class="{ error: hasError }">{{ message }}</p>
      <button type="submit">创建账号</button>
      <RouterLink class="switch-link" to="/login">
        已有账号？去登录
      </RouterLink>
    </form>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { authAPI } from "../utils/api";

const router = useRouter();
const form = reactive({ username: "", email: "", password: "", code: "" });
const confirmPassword = ref("");
const accepted = ref(false);
const message = ref("");
const hasError = ref(false);

async function sendCode() {
  hasError.value = false;
  try {
    await authAPI.sendCode(form.email);
    message.value = "验证码已发送";
  } catch (err) {
    hasError.value = true;
    message.value = err.response?.data?.msg || "验证码发送失败，请稍后重试";
  }
}

async function submit() {
  hasError.value = true;
  if (form.password !== confirmPassword.value) {
    message.value = "两次输入的密码不一致";
    return;
  }
  if (!accepted.value) {
    message.value = "请先同意用户协议和隐私政策";
    return;
  }
  try {
    await authAPI.register(form);
    router.push("/login");
  } catch (err) {
    message.value = err.response?.data?.msg || "注册失败，请检查信息后重试";
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
    #ffffff;
  padding: 24px;
}

.auth-panel {
  display: grid;
  gap: 16px;
  width: min(480px, 100%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-large);
  background: rgba(255, 255, 255, 0.94);
  padding: 34px;
  box-shadow: var(--shadow-card);
}

.brand {
  color: var(--color-primary);
  font-weight: 850;
  text-decoration: none;
}

p {
  margin: 0 0 6px;
  color: var(--color-muted);
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
  padding: 13px 14px;
}

.code-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: end;
}

.check {
  grid-template-columns: auto 1fr;
  align-items: center;
  color: var(--color-text);
}

.check input {
  width: 18px;
  height: 18px;
}

button {
  border: 0;
  border-radius: var(--radius-pill);
  background: var(--color-primary);
  color: #ffffff;
  padding: 13px 16px;
  font-weight: 850;
  box-shadow: 0 14px 28px rgba(255, 112, 88, 0.18);
}

.secondary {
  border: 1px solid var(--color-border);
  background: #ffffff;
  color: var(--color-heading);
  box-shadow: none;
}

.switch-link {
  color: var(--color-primary);
  text-align: center;
  text-decoration: none;
  font-weight: 750;
}

.error {
  color: #b91c1c;
}

@media (max-width: 560px) {
  .code-row {
    grid-template-columns: 1fr;
  }
}
</style>
