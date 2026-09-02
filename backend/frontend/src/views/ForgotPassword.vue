<template>
  <div class="auth-page">
    <form class="auth-panel" novalidate @submit.prevent="submitReset">
      <RouterLink class="brand" to="/">知航屿</RouterLink>
      <div class="auth-heading">
        <p>找回你的账号</p>
        <h1>重置密码</h1>
      </div>

      <label>
        注册邮箱
        <div class="verification-field">
          <input
            v-model.trim="email"
            autocomplete="email"
            inputmode="email"
            type="email"
            placeholder="name@example.com"
            required
            @input="clearMessage"
          />
          <button
            class="send-code"
            type="button"
            :disabled="sendingCode || countdown > 0 || resetting"
            @click="sendCode"
          >
            {{
              sendingCode
                ? "发送中…"
                : countdown > 0
                  ? `${countdown} 秒后重发`
                  : "发送验证码"
            }}
          </button>
        </div>
      </label>

      <label>
        六位验证码
        <input
          v-model="code"
          autocomplete="one-time-code"
          inputmode="numeric"
          maxlength="6"
          pattern="[0-9]{6}"
          placeholder="请输入邮件中的验证码"
          required
          @input="normalizeCode"
        />
      </label>

      <label>
        新密码
        <div class="password-field">
          <input
            v-model="newPassword"
            autocomplete="new-password"
            :type="showNewPassword ? 'text' : 'password'"
            placeholder="至少 8 位，包含字母和数字"
            required
            @input="clearMessage"
          />
          <button
            class="visibility-button"
            type="button"
            :aria-label="showNewPassword ? '隐藏新密码' : '显示新密码'"
            :title="showNewPassword ? '隐藏新密码' : '显示新密码'"
            @click="showNewPassword = !showNewPassword"
          >
            <EyeOff v-if="showNewPassword" :size="19" aria-hidden="true" />
            <Eye v-else :size="19" aria-hidden="true" />
          </button>
        </div>
      </label>

      <label>
        确认新密码
        <div class="password-field">
          <input
            v-model="confirmPassword"
            autocomplete="new-password"
            :type="showConfirmPassword ? 'text' : 'password'"
            placeholder="再次输入新密码"
            required
            @input="clearMessage"
          />
          <button
            class="visibility-button"
            type="button"
            :aria-label="showConfirmPassword ? '隐藏确认密码' : '显示确认密码'"
            :title="showConfirmPassword ? '隐藏确认密码' : '显示确认密码'"
            @click="showConfirmPassword = !showConfirmPassword"
          >
            <EyeOff v-if="showConfirmPassword" :size="19" aria-hidden="true" />
            <Eye v-else :size="19" aria-hidden="true" />
          </button>
        </div>
      </label>

      <p v-if="message" :class="messageType">{{ message }}</p>
      <button class="submit-button" type="submit" :disabled="resetting || sendingCode">
        {{ resetting ? "重置中…" : "重置密码" }}
      </button>
      <RouterLink class="switch-link" to="/login">返回登录页面</RouterLink>
    </form>
  </div>
</template>

<script setup>
import axios from "axios";
import { Eye, EyeOff } from "lucide-vue-next";
import { onBeforeUnmount, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { API_BASE_URL, authAPI } from "../utils/api";
import { successToast } from "../utils/toast";

const router = useRouter();
const email = ref("");
const code = ref("");
const newPassword = ref("");
const confirmPassword = ref("");
const showNewPassword = ref(false);
const showConfirmPassword = ref(false);
const sendingCode = ref(false);
const resetting = ref(false);
const countdown = ref(0);
const message = ref("");
const messageType = ref("error");
const sentEmail = ref("");
let countdownTimer = null;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const STRONG_PASSWORD_PATTERN = /^(?=.*[A-Za-z])(?=.*\d).{8,}$/;

function normalizedEmail() {
  return email.value.trim().toLowerCase();
}

function clearTimer() {
  if (countdownTimer) clearInterval(countdownTimer);
  countdownTimer = null;
  countdown.value = 0;
}

function startCountdown() {
  clearTimer();
  countdown.value = 60;
  countdownTimer = setInterval(() => {
    countdown.value -= 1;
    if (countdown.value <= 0) clearTimer();
  }, 1000);
}

function clearMessage() {
  message.value = "";
}

function showError(value) {
  messageType.value = "error";
  message.value = value;
}

function normalizeCode() {
  code.value = code.value.replace(/\D/g, "").slice(0, 6);
  clearMessage();
}

function requestErrorMessage(error, fallback) {
  const backendMessage = error?.response?.data?.message || error?.response?.data?.msg;
  if (backendMessage) return backendMessage;

  const responseCode = error?.response?.data?.code;
  const messages = {
    EMAIL_REQUIRED: "请输入邮箱地址",
    EMAIL_INVALID: "邮箱格式不正确",
    RESET_CODE_RATE_LIMITED: "验证码发送过于频繁，请稍后再试",
    RESET_CODE_HOURLY_LIMIT: "验证码发送次数已达上限，请稍后再试",
    RESET_CODE_INVALID: "验证码错误，请检查后重试",
    RESET_CODE_EXPIRED: "验证码已过期，请重新获取",
    RESET_CODE_USED: "验证码已使用，请重新获取",
    RESET_CODE_LOCKED: "验证码错误次数过多，请重新获取",
    PASSWORD_WEAK: "新密码至少 8 位，并且至少包含一个字母和一个数字",
    PASSWORD_MISMATCH: "两次输入的密码不一致",
    MAIL_CONFIG_MISSING: "邮件服务尚未完成配置，请联系管理员",
    PASSWORD_RESET_UNAVAILABLE: "密码重置服务暂不可用，请稍后重试",
  };
  if (messages[responseCode]) return messages[responseCode];
  if (error?.response?.status === 400) return "请输入正确的邮箱地址";
  if (error?.response?.status === 429) return "操作过于频繁，请稍后重试";
  if (error?.response?.status === 503) return "邮件服务暂时不可用";
  if (axios.isCancel(error) || error?.code === "ERR_CANCELED") {
    return "请求已取消，请重新提交";
  }
  if (
    error?.code === "ECONNABORTED" ||
    error?.code === "ETIMEDOUT" ||
    String(error?.message || "").toLowerCase().includes("timeout")
  ) {
    return "请求超时，请稍后重试";
  }
  if (!error?.response) return "无法连接服务器，请检查后端服务";
  return fallback;
}

function safeDiagnosticData(value) {
  if (!value || typeof value !== "object") return value;
  if (Array.isArray(value)) return value.map(safeDiagnosticData);
  const sensitiveKeys = new Set([
    "test_code",
    "verification_code",
    "password",
    "new_password",
    "confirm_password",
    "mail_password",
    "authorization",
  ]);
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      key,
      sensitiveKeys.has(key.toLowerCase()) ? "[REDACTED]" : safeDiagnosticData(item),
    ]),
  );
}

function logSendCodeResult(response, error = null) {
  if (!import.meta.env.DEV) return;
  const status = response?.status ?? error?.response?.status ?? "NETWORK_ERROR";
  const data = response?.data ?? error?.response?.data ?? null;
  console.info(
    `[password-reset] send-code ${JSON.stringify({
      url: `${API_BASE_URL.replace(/\/$/, "")}/auth/forgot-password/send-code`,
      status,
      response: safeDiagnosticData(data),
    })}`,
  );
}

async function sendCode() {
  if (sendingCode.value || resetting.value || countdown.value > 0) return;
  const value = normalizedEmail();
  if (!EMAIL_PATTERN.test(value)) return showError("请输入有效的邮箱地址");

  sendingCode.value = true;
  clearMessage();
  try {
    const response = await authAPI.sendPasswordResetCode(value);
    logSendCodeResult(response);
    sentEmail.value = value;
    messageType.value = "success";
    message.value =
      response?.data?.message || "如果该邮箱已注册，验证码将发送至该邮箱";
    startCountdown();
  } catch (error) {
    logSendCodeResult(null, error);
    showError(requestErrorMessage(error, "验证码发送失败，请稍后重试"));
  } finally {
    sendingCode.value = false;
  }
}

async function submitReset() {
  if (resetting.value || sendingCode.value) return;
  const value = normalizedEmail();
  if (!EMAIL_PATTERN.test(value)) return showError("请输入有效的邮箱地址");
  if (!/^\d{6}$/.test(code.value)) return showError("请输入六位数字验证码");
  if (!STRONG_PASSWORD_PATTERN.test(newPassword.value)) {
    return showError("新密码至少 8 位，并且至少包含一个字母和一个数字");
  }
  if (newPassword.value !== confirmPassword.value) {
    return showError("两次输入的密码不一致");
  }

  resetting.value = true;
  clearMessage();
  try {
    await authAPI.resetPassword({
      email: value,
      code: code.value,
      new_password: newPassword.value,
      confirm_password: confirmPassword.value,
    });
    email.value = "";
    code.value = "";
    newPassword.value = "";
    confirmPassword.value = "";
    sentEmail.value = "";
    clearTimer();
    successToast("密码重置成功，请使用新密码登录");
    await router.replace({ path: "/login", query: { reset: "success" } });
  } catch (error) {
    showError(requestErrorMessage(error, "密码重置失败，请稍后重试"));
  } finally {
    resetting.value = false;
  }
}

watch(email, () => {
  if (sentEmail.value && normalizedEmail() !== sentEmail.value) {
    sentEmail.value = "";
    code.value = "";
    clearTimer();
  }
});

onBeforeUnmount(clearTimer);
</script>

<style scoped>
.auth-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 12% 20%, rgba(191, 245, 237, 0.42), transparent 28%),
    radial-gradient(circle at 90% 30%, rgba(255, 112, 88, 0.16), transparent 30%),
    linear-gradient(180deg, #ffffff 0%, #fffaf8 100%);
}

.auth-panel {
  display: grid;
  gap: 18px;
  width: min(520px, 100%);
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

.verification-field {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}

input {
  width: 100%;
  min-width: 0;
  padding: 13px 14px;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: #ffffff;
}

.password-field {
  position: relative;
}

.password-field input {
  padding-right: 46px;
}

button {
  border: 0;
  font: inherit;
}

.submit-button {
  padding: 14px 16px;
  border-radius: var(--radius-pill);
  background: var(--color-primary);
  color: #ffffff;
  font-weight: 850;
  box-shadow: 0 14px 28px rgba(255, 112, 88, 0.18);
}

.send-code {
  min-width: 122px;
  padding: 10px 14px;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-pill);
  background: #ffffff;
  color: var(--color-primary);
  font-weight: 850;
}

.visibility-button {
  position: absolute;
  top: 50%;
  right: 6px;
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  padding: 0;
  transform: translateY(-50%);
  border-radius: 50%;
  background: transparent;
  color: #64748b;
}

button:disabled {
  cursor: wait;
  opacity: 0.62;
}

.visibility-button:hover:not(:disabled) {
  background: #f1f5f9;
  color: var(--color-heading);
}

.switch-link {
  text-align: center;
}

.error,
.success {
  margin: 0;
  font-weight: 750;
}

.error {
  color: #b91c1c;
}

.success {
  color: #15803d;
}

@media (max-width: 520px) {
  .verification-field {
    grid-template-columns: 1fr;
  }

  .send-code {
    width: 100%;
  }
}
</style>
