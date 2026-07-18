<template>
  <div class="auth-page">
    <form class="auth-panel" @submit.prevent="submit">
      <RouterLink class="brand" to="/">智汇导航</RouterLink>
      <div class="auth-heading">
        <p>开启个性化推荐</p>
        <h1>注册账号</h1>
      </div>
      <label>
        用户名
        <input v-model.trim="form.username" autocomplete="username" required />
      </label>
      <label>
        邮箱
        <input
          v-model.trim="form.email"
          autocomplete="email"
          type="email"
          required
        />
      </label>
      <label>
        密码
        <input
          v-model="form.password"
          autocomplete="new-password"
          type="password"
          required
        />
      </label>
      <label>
        确认密码
        <input
          v-model="confirmPassword"
          autocomplete="new-password"
          type="password"
          required
        />
      </label>
      <div class="code-row">
        <label>
          邮箱验证码
          <input v-model.trim="form.code" required />
        </label>
        <button
          type="button"
          class="secondary"
          :disabled="codeLoading || submitLoading"
          @click="sendCode"
        >
          {{ codeLoading ? "发送中..." : "发送验证码" }}
        </button>
      </div>
      <label class="check">
        <input v-model="accepted" type="checkbox" />
        我已阅读并同意用户协议和隐私政策
      </label>
      <p v-if="message" :class="{ error: hasError, success: !hasError }">
        {{ message }}
      </p>
      <button type="submit" :disabled="submitLoading">
        {{ submitLoading ? "处理中..." : "创建账号" }}
      </button>
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
import { errorToast, successToast } from "../utils/toast";

const router = useRouter();
const form = reactive({ username: "", email: "", password: "", code: "" });
const confirmPassword = ref("");
const accepted = ref(false);
const message = ref("");
const hasError = ref(false);
const codeLoading = ref(false);
const submitLoading = ref(false);

function isEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function setError(value) {
  hasError.value = true;
  message.value = value;
  errorToast(value);
}

async function sendCode() {
  if (codeLoading.value) return;
  if (!isEmail(form.email)) {
    setError("请输入正确的邮箱地址");
    return;
  }
  codeLoading.value = true;
  hasError.value = false;
  try {
    await authAPI.sendCode(form.email);
    message.value = "验证码已发送";
    successToast("验证码已发送");
  } catch (err) {
    hasError.value = true;
    message.value = err.response?.data?.msg || "验证码发送失败，请稍后重试";
    errorToast(message.value);
  } finally {
    codeLoading.value = false;
  }
}

async function submit() {
  if (submitLoading.value) return;
  if (!form.username.trim()) {
    setError("请输入用户名");
    return;
  }
  if (!isEmail(form.email)) {
    setError("请输入正确的邮箱地址");
    return;
  }
  if (!form.password) {
    setError("请输入密码");
    return;
  }
  if (form.password.length < 8) {
    setError("密码至少需要 8 位");
    return;
  }
  if (form.password !== confirmPassword.value) {
    setError("两次输入的密码不一致");
    return;
  }
  if (!form.code.trim()) {
    setError("请输入验证码");
    return;
  }
  if (!accepted.value) {
    setError("请先同意用户协议和隐私政策");
    return;
  }
  submitLoading.value = true;
  hasError.value = false;
  try {
    await authAPI.register(form);
    successToast("注册成功，请登录");
    router.push("/login");
  } catch (err) {
    hasError.value = true;
    message.value = err.response?.data?.msg || "注册失败，请检查信息后重试";
    errorToast(message.value);
  } finally {
    submitLoading.value = false;
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
  width: min(500px, 100%);
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

.code-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
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
  padding: 14px 16px;
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
  transform: none;
}

.secondary {
  border: 1px solid rgba(255, 112, 88, 0.28);
  background: var(--color-soft-orange);
  color: var(--color-primary);
  box-shadow: none;
}

.secondary:hover,
.secondary:focus-visible {
  background: #ffe8e0;
  color: var(--color-primary-dark);
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
  color: #b91c1c;
}

.success {
  color: #047857;
}

@media (max-width: 560px) {
  .code-row {
    grid-template-columns: 1fr;
  }
}
</style>
