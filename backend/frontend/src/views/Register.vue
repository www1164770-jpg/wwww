<template>
  <div class="auth-page">
    <form class="auth-panel" @submit.prevent="submit">
      <RouterLink class="brand" to="/">知航屿</RouterLink>
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
        邮箱验证码
        <div class="verification-field">
          <input
            v-model.trim="verificationCode"
            type="text"
            inputmode="numeric"
            autocomplete="one-time-code"
            maxlength="6"
            placeholder="请输入邮箱验证码"
            required
          />
          <button
            class="send-code"
            type="button"
            :disabled="
              isSendingCode || countdown > 0 || !isValidEmail(form.email)
            "
            @click="sendVerificationCode"
          >
            {{
              isSendingCode
                ? "发送中..."
                : countdown > 0
                  ? `${countdown}s 后重发`
                  : "发送验证码"
            }}
          </button>
        </div>
        <span v-if="codeError" class="field-error">{{ codeError }}</span>
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
      <label class="check">
        <input v-model="accepted" type="checkbox" />
        我已阅读并同意用户协议和隐私政策
      </label>
      <p v-if="message" :class="{ error: hasError, success: !hasError }">
        {{ message }}
        <RouterLink v-if="showLoginLink" to="/login" class="inline-login-link"
          >前往登录</RouterLink
        >
      </p>
      <button type="submit" :disabled="submitLoading">
        {{ submitLoading ? "正在创建…" : "创建账号" }}
      </button>
      <RouterLink class="switch-link" to="/login">
        已有账号？前往登录
      </RouterLink>
    </form>
  </div>
</template>

<script setup>
import { onBeforeUnmount, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { authAPI } from "../utils/api";
import { errorToast, successToast } from "../utils/toast";

const router = useRouter();
const form = reactive({ username: "", email: "", password: "" });
const confirmPassword = ref("");
const verificationCode = ref("");
const accepted = ref(false);
const message = ref("");
const hasError = ref(false);
const submitLoading = ref(false);
const isSendingCode = ref(false);
const countdown = ref(0);
const codeError = ref("");
const showLoginLink = ref(false);
let countdownTimer = null;

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function resetVerificationState() {
  verificationCode.value = "";
  codeError.value = "";
  countdown.value = 0;
  showLoginLink.value = false;
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
}

function startCountdown() {
  if (countdownTimer) clearInterval(countdownTimer);
  countdown.value = 60;
  countdownTimer = setInterval(() => {
    countdown.value -= 1;
    if (countdown.value <= 0) {
      clearInterval(countdownTimer);
      countdownTimer = null;
    }
  }, 1000);
}

function getVerificationErrorMessage(error) {
  const code = error?.response?.data?.code;
  const messages = {
    EMAIL_REQUIRED: "请输入邮箱地址",
    EMAIL_INVALID: "邮箱格式不正确",
    EMAIL_ALREADY_REGISTERED: "该邮箱已注册，请直接登录",
    CODE_RATE_LIMITED: "验证码发送过于频繁，请稍后再试",
    RATE_LIMITED: "操作过于频繁，请稍后再试",
    MAIL_CONFIG_MISSING: "邮件服务尚未完成配置，请联系管理员",
    MAIL_NOT_CONFIGURED: "邮件服务尚未配置",
    SMTP_DNS_FAILED: "无法解析邮件服务器地址",
    SMTP_CONNECTION_TIMEOUT: "连接邮件服务器超时，请稍后重试",
    SMTP_CONNECTION_FAILED: "邮件服务器连接失败，请稍后重试",
    SMTP_SSL_FAILED: "邮件服务器安全连接失败，请联系管理员",
    SMTP_AUTH_FAILED: "QQ 邮箱 SMTP 认证失败，请联系管理员检查授权码",
    SMTP_SENDER_REJECTED: "发件邮箱被邮件服务器拒绝",
    SMTP_RECIPIENT_REJECTED: "收件邮箱被邮件服务器拒绝",
    SMTP_SEND_FAILED: "邮件发送失败，请稍后重试",
    DATABASE_FAILED: "验证码服务暂不可用，请稍后重试",
    MAIL_AUTH_FAILED: "邮件服务认证失败，请联系管理员检查 SMTP 授权码",
    MAIL_CONNECTION_FAILED: "邮件服务器连接失败，请稍后重试",
    MAIL_RECIPIENT_REJECTED: "收件邮箱被邮件服务器拒绝",
    MAIL_SENDER_REJECTED: "发件邮箱被邮件服务器拒绝",
    MAIL_SEND_FAILED: "邮件发送失败，请稍后重试",
    VERIFICATION_STORAGE_UNAVAILABLE: "验证码服务暂不可用，请稍后重试",
  };
  return (
    messages[code] ||
    error?.response?.data?.message ||
    "验证码发送失败，请稍后重试"
  );
}

function getRegisterErrorMessage(error) {
  const messages = {
    USERNAME_REQUIRED: "请输入用户名",
    USERNAME_INVALID: "用户名格式不正确",
    USERNAME_EXISTS: "该用户名已被使用",
    EMAIL_INVALID: "邮箱格式不正确",
    EMAIL_ALREADY_REGISTERED: "该邮箱已注册，请直接登录",
    PASSWORD_REQUIRED: "请输入密码",
    PASSWORD_TOO_SHORT: "密码长度不足",
    CODE_REQUIRED: "请输入邮箱验证码",
    CODE_NOT_FOUND: "请先获取验证码",
    CODE_INVALID: "验证码错误",
    CODE_EXPIRED: "验证码已过期，请重新获取",
    CODE_TOO_MANY_ATTEMPTS: "验证码错误次数过多，请重新获取",
    CODE_ALREADY_USED: "验证码已使用，请重新获取",
    REGISTRATION_UNAVAILABLE: "注册服务暂不可用，请稍后重试",
    VERIFICATION_STORAGE_UNAVAILABLE: "验证码服务暂不可用，请稍后重试",
    DATABASE_ERROR: "账号创建失败，请稍后重试",
  };
  const code = error?.response?.data?.code;
  return (
    messages[code] ||
    error?.response?.data?.message ||
    error?.response?.data?.msg ||
    "注册失败，请稍后重试"
  );
}

function isEmailAlreadyRegisteredError(error) {
  return error?.response?.data?.code === "EMAIL_ALREADY_REGISTERED";
}

async function sendVerificationCode() {
  if (isSendingCode.value || countdown.value > 0) return;
  const email = form.email.trim().toLowerCase();
  codeError.value = "";
  if (!isValidEmail(email)) {
    codeError.value = "请输入有效的邮箱地址";
    return;
  }

  isSendingCode.value = true;
  try {
    await authAPI.sendRegisterCode({ email });
    startCountdown();
    successToast("验证码已发送，请检查邮箱");
  } catch (error) {
    const code = error?.response?.data?.code;
    if (code === "EMAIL_ALREADY_REGISTERED") {
      showLoginLink.value = true;
      codeError.value = "该邮箱已注册，请直接登录";
    } else {
      codeError.value = getVerificationErrorMessage(error);
    }
    errorToast(codeError.value);
  } finally {
    isSendingCode.value = false;
  }
}

function setError(value, loginLink = false) {
  hasError.value = true;
  message.value = value;
  showLoginLink.value = loginLink;
  errorToast(value);
}

async function submit() {
  if (submitLoading.value) return;
  if (!form.username.trim()) return setError("请输入用户名");
  if (!isValidEmail(form.email)) return setError("请输入正确的邮箱地址");
  if (!/^\d{6}$/.test(verificationCode.value)) {
    return setError("请输入 6 位邮箱验证码");
  }
  if (!form.password) return setError("请输入密码");
  if (form.password.length < 8) return setError("密码至少需要 8 位");
  if (form.password !== confirmPassword.value) {
    return setError("两次输入的密码不一致");
  }
  if (!accepted.value) return setError("请先同意用户协议和隐私政策");

  submitLoading.value = true;
  hasError.value = false;
  message.value = "";
  showLoginLink.value = false;
  try {
    await authAPI.register({
      username: form.username.trim(),
      email: form.email.trim().toLowerCase(),
      password: form.password,
      verification_code: verificationCode.value,
    });
  } catch (error) {
    const needsLoginLink = isEmailAlreadyRegisteredError(error);
    setError(getRegisterErrorMessage(error), needsLoginLink);
    return;
  } finally {
    submitLoading.value = false;
  }

  successToast("注册成功，请登录");
  await router.push("/login?registered=1");
}

watch(
  () => form.email,
  () => resetVerificationState(),
);

onBeforeUnmount(() => {
  if (countdownTimer) clearInterval(countdownTimer);
});
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
  width: min(500px, 100%);
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

.verification-field input {
  min-width: 0;
}

button.send-code {
  min-width: 112px;
  padding: 10px 14px;
  border: 1px solid var(--color-primary);
  background: #ffffff;
  color: var(--color-primary);
  box-shadow: none;
}

button.send-code:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.field-error {
  color: #d14343;
  font-size: 13px;
  font-weight: 650;
}

input {
  min-width: 0;
  padding: 13px 14px;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: #ffffff;
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
  padding: 14px 16px;
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

.inline-login-link {
  margin-left: 6px;
  color: var(--color-primary);
  font-weight: 850;
  text-decoration: underline;
}

.success {
  margin: 0;
  color: #15803d;
  font-weight: 750;
}
</style>
