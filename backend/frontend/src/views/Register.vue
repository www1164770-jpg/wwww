<template>
  <div class="auth-page">
    <form class="auth-panel" @submit.prevent="submit">
      <RouterLink class="brand" to="/">AI Nav</RouterLink>
      <h1>注册账号</h1>
      <label>用户名<input v-model.trim="form.username" required /></label>
      <label
        >邮箱<input v-model.trim="form.email" type="email" required
      /></label>
      <label
        >密码<input v-model="form.password" type="password" required
      /></label>
      <label
        >确认密码<input v-model="confirmPassword" type="password" required
      /></label>
      <div class="code-row">
        <label>邮箱验证码<input v-model.trim="form.code" required /></label>
        <button type="button" @click="sendCode">发送验证码</button>
      </div>
      <label class="check">
        <input v-model="accepted" type="checkbox" />
        我已阅读并同意用户协议和隐私政策
      </label>
      <p v-if="message" :class="{ error: hasError }">{{ message }}</p>
      <button type="submit">创建账号</button>
      <RouterLink to="/login">已有账号？去登录</RouterLink>
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
    message.value = err.response?.data?.msg || "验证码发送失败";
  }
}

async function submit() {
  hasError.value = true;
  if (form.password !== confirmPassword.value) {
    message.value = "两次输入的密码不一致";
    return;
  }
  if (!accepted.value) {
    message.value = "请先同意用户协议";
    return;
  }
  try {
    await authAPI.register(form);
    router.push("/login");
  } catch (err) {
    message.value = err.response?.data?.msg || "注册失败";
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
  width: min(460px, 100%);
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
label {
  display: grid;
  gap: 8px;
  font-weight: 700;
}
input {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 12px;
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
}
button {
  border: 0;
  border-radius: 8px;
  background: #111827;
  color: #fff;
  padding: 12px 14px;
  font-weight: 800;
}
.error {
  color: #b91c1c;
}
</style>
