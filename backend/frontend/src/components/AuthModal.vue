<template>
  <!-- 🔐 登录 / 注册弹窗 -->
  <div v-if="show" class="auth-overlay" @click="close">
    <div class="auth-modal" @click.stop>
      <button class="close-btn" @click="close">×</button>
      <transition name="fade-slide" mode="out-in">
        <!-- 选择登录方式 -->
        <div v-if="stage === 'methods'" key="methods" class="vertical-layout">
          <h2 class="modal-title">快速登录 / 注册</h2>
          <button class="method-btn github" @click="handleGithubLogin">
            🐱 GitHub 登录
          </button>
          <button class="method-btn phone" @click="switchTo('mobile')">
            📱 手机号验证码
          </button>
          <button class="method-btn email" @click="switchTo('email')">
            ✉️ 邮箱密码登录
          </button>
          <button
            class="method-btn register"
            @click="switchTo('register')"
            style="margin-top: 10px; border-color: #3b82f6; color: #3b82f6"
          >
            ✨ 新用户注册
          </button>
          <button
            class="link-btn"
            @click="switchTo('reset')"
            style="margin-top: 6px; font-size: 12px; color: #94a3b8"
          >
            忘记密码？
          </button>
        </div>

        <!-- 手机号登录 -->
        <div
          v-else-if="stage === 'mobile'"
          key="mobile"
          class="vertical-layout"
        >
          <h2 class="modal-title">手机号登录</h2>
          <input
            type="text"
            v-model="phoneNumber"
            placeholder="请输入手机号"
            class="auth-input"
          />
          <div class="verify-code-row">
            <input
              type="text"
              v-model="verifyCode"
              placeholder="验证码"
              class="auth-input small"
            />
            <button class="get-code-btn" @click="handleSmsLogin">
              {{ smsCountdown > 0 ? `${smsCountdown}s 后重发` : "获取验证码" }}
            </button>
          </div>
          <button class="btn-submit" @click="handleMobileLogin">
            立即登录
          </button>
          <button class="link-btn" @click="switchTo('methods')">
            返回其他方式
          </button>
        </div>

        <!-- 邮箱密码登录 -->
        <div v-else-if="stage === 'email'" key="email" class="vertical-layout">
          <h2 class="modal-title">邮箱密码登录</h2>
          <input
            type="email"
            v-model="loginForm.email"
            placeholder="请输入邮箱地址"
            class="auth-input"
          />
          <input
            type="password"
            v-model="loginForm.password"
            placeholder="请输入密码"
            class="auth-input"
          />
          <button class="btn-submit" @click="handleEmailLogin">确认登录</button>
          <button class="link-btn" @click="switchTo('methods')">
            返回其他方式
          </button>
        </div>

        <!-- 新用户注册 -->
        <div
          v-else-if="stage === 'register'"
          key="register"
          class="vertical-layout"
        >
          <h2 class="modal-title">新用户注册</h2>
          <input
            type="text"
            v-model="regForm.username"
            placeholder="给你的账号起个好听的名字"
            class="auth-input"
          />
          <input
            type="email"
            v-model="regForm.email"
            placeholder="请输入常用邮箱"
            class="auth-input"
          />
          <div class="verify-code-row">
            <input
              type="text"
              v-model="regForm.code"
              placeholder="6位验证码"
              class="auth-input small"
            />
            <button
              class="get-code-btn"
              :disabled="regCountdown > 0"
              @click="sendRegCode"
            >
              {{ regCountdown > 0 ? `${regCountdown}s 后重发` : "获取验证码" }}
            </button>
          </div>
          <input
            type="password"
            v-model="regForm.password"
            placeholder="设置一个强密码"
            class="auth-input"
          />
          <div class="terms-row" style="margin-top: 5px">
            <label
              class="terms-label"
              style="
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 12px;
                color: #64748b;
                cursor: pointer;
              "
            >
              <input
                type="checkbox"
                v-model="regForm.agreeTerms"
                style="width: 14px; height: 14px; cursor: pointer"
              />
              <span
                >我已阅读并同意
                <a
                  href="/terms"
                  target="_blank"
                  style="
                    color: #3b82f6;
                    text-decoration: none;
                    font-weight: bold;
                  "
                  >用户协议</a
                >
                与
                <a
                  href="/privacy"
                  target="_blank"
                  style="
                    color: #3b82f6;
                    text-decoration: none;
                    font-weight: bold;
                  "
                  >隐私政策</a
                ></span
              >
            </label>
          </div>
          <button class="btn-submit" @click="handleRegister">立即注册</button>
          <button class="link-btn" @click="switchTo('methods')">
            返回其他方式
          </button>
        </div>

        <!-- 🔑 忘记密码 -->
        <div v-else-if="stage === 'reset'" key="reset" class="vertical-layout">
          <h2 class="modal-title">找回密码</h2>
          <p
            style="
              font-size: 13px;
              color: #64748b;
              text-align: center;
              margin-bottom: 12px;
            "
          >
            输入注册邮箱，我们将发送重置链接
          </p>

          <!-- 步骤 1：输入邮箱 -->
          <template v-if="resetStep === 1">
            <input
              type="email"
              v-model="resetForm.email"
              placeholder="请输入注册时使用的邮箱"
              class="auth-input"
            />
            <button class="btn-submit" @click="sendResetCode">
              发送重置验证码
            </button>
          </template>

          <!-- 步骤 2：输入验证码 + 新密码 -->
          <template v-else-if="resetStep === 2">
            <div class="verify-code-row">
              <input
                type="text"
                v-model="resetForm.code"
                placeholder="6位验证码"
                class="auth-input small"
              />
              <button
                class="get-code-btn"
                :disabled="resetCountdown > 0"
                @click="sendResetCode"
              >
                {{
                  resetCountdown > 0 ? `${resetCountdown}s 后重发` : "重新发送"
                }}
              </button>
            </div>
            <input
              type="password"
              v-model="resetForm.newPassword"
              placeholder="请输入新密码（至少6位）"
              class="auth-input"
            />
            <button class="btn-submit" @click="confirmResetPassword">
              重置密码并登录
            </button>
          </template>
          <button class="link-btn" @click="switchTo('methods')">
            返回其他方式
          </button>
        </div>
      </transition>
      <div class="modal-footer">
        注册/登录即代表同意 <a href="#" target="_blank">用户协议</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";
import { authAPI } from "@/utils/api";
import { useUserStore } from "@/stores/user";

const emit = defineEmits(["toast", "close"]);
const props = defineProps({ show: { type: Boolean, default: false } });

const userStore = useUserStore();

// --- 阶段切换 ---
const stage = ref("methods");
const resetStep = ref(1);

function switchTo(s) {
  stage.value = s;
  if (s === "reset") resetStep.value = 1;
}

function close() {
  emit("close");
}

// --- 登录表单 ---
const loginForm = reactive({ email: "", password: "" });
const phoneNumber = ref("");
const verifyCode = ref("");
const smsCountdown = ref(0);
let smsTimer = null;

// --- 注册表单 ---
const regForm = reactive({
  username: "",
  email: "",
  password: "",
  code: "",
  agreeTerms: false,
});
const regCountdown = ref(0);
let regTimer = null;

// --- 重置密码表单 ---
const resetForm = reactive({ email: "", code: "", newPassword: "" });
const resetCountdown = ref(0);
let resetTimer = null;

// --- 发送注册验证码 ---
const sendRegCode = async () => {
  if (!regForm.email.includes("@"))
    return emit("toast", "⚠️ 请输入有效的邮箱格式！", "error");
  if (regCountdown.value > 0) return;
  regCountdown.value = 60;
  regTimer = setInterval(() => {
    regCountdown.value--;
    if (regCountdown.value <= 0) clearInterval(regTimer);
  }, 1000);
  try {
    const res = await authAPI.sendCode(regForm.email);
    if (res.data.code === 0) {
      emit("toast", "📧 验证码已发送，请查收邮箱", "success");
    } else {
      clearInterval(regTimer);
      regCountdown.value = 0;
      emit("toast", "❌ " + res.data.msg, "error");
    }
  } catch (error) {
    clearInterval(regTimer);
    regCountdown.value = 0;
    emit(
      "toast",
      "❌ 发送失败：" + (error.response?.data?.msg || "网络错误"),
      "error",
    );
  }
};

// --- 提交注册 ---
const handleRegister = async () => {
  if (!regForm.agreeTerms)
    return emit("toast", "⚠️ 请先阅读并勾选用户协议和隐私政策！", "error");
  if (
    !regForm.username ||
    !regForm.email ||
    !regForm.password ||
    !regForm.code
  ) {
    return emit("toast", "⚠️ 请填写完整的注册信息！", "error");
  }
  try {
    const res = await authAPI.register(regForm);
    if (res.data.code === 0) {
      emit("toast", "🎉 注册成功！快去登录吧", "success");
      regForm.username = "";
      regForm.email = "";
      regForm.password = "";
      regForm.code = "";
      regForm.agreeTerms = false;
      switchTo("email");
    } else {
      emit("toast", "❌ 注册失败：" + res.data.msg, "error");
    }
  } catch (error) {
    emit(
      "toast",
      "❌ 网络或服务错误：" + (error.response?.data?.msg || "请检查控制台"),
      "error",
    );
  }
};

// --- 邮箱登录 ---
const handleEmailLogin = async () => {
  if (!loginForm.email || !loginForm.password) {
    return emit("toast", "⚠️ 请填写邮箱和密码", "error");
  }
  try {
    const res = await authAPI.login(loginForm.email, loginForm.password);
    if (res.data.code === 0) {
      userStore.setLoginSuccess(res.data.token, res.data.refresh_token);
      emit("toast", "🎉 登录成功！", "success");
      close();
    } else {
      emit("toast", "❌ " + res.data.msg, "error");
    }
  } catch (error) {
    emit(
      "toast",
      "❌ " + (error.response?.data?.msg || "账号或密码错误"),
      "error",
    );
  }
};

// --- 手机登录 ---
const handleMobileLogin = () => {
  // TODO: 手机号验证码登录逻辑
  emit("toast", "📱 手机登录功能开发中", "info");
};

const handleSmsLogin = () => {
  // TODO: 发送短信登录验证码
  emit("toast", "📱 短信功能开发中", "info");
};

// --- GitHub 登录 ---
const handleGithubLogin = () => {
  window.location.href = authAPI.githubLoginUrl;
};

// --- 🔑 发送密码重置验证码 ---
const sendResetCode = async () => {
  if (!resetForm.email.includes("@"))
    return emit("toast", "⚠️ 请输入有效的邮箱格式！", "error");
  if (resetCountdown.value > 0) return;
  resetCountdown.value = 60;
  resetTimer = setInterval(() => {
    resetCountdown.value--;
    if (resetCountdown.value <= 0) clearInterval(resetTimer);
  }, 1000);
  try {
    const res = await authAPI.sendResetCode(resetForm.email);
    if (res.data.code === 0) {
      emit("toast", "📧 验证码已发送，请查收邮箱", "success");
      resetStep.value = 2;
    } else {
      clearInterval(resetTimer);
      resetCountdown.value = 0;
      emit("toast", "❌ " + res.data.msg, "error");
    }
  } catch (error) {
    clearInterval(resetTimer);
    resetCountdown.value = 0;
    emit("toast", "❌ 发送失败，请确认邮箱是否已注册", "error");
  }
};

// --- 🔑 确认重置密码 ---
const confirmResetPassword = async () => {
  if (!resetForm.code) return emit("toast", "⚠️ 请输入验证码", "error");
  if (!resetForm.newPassword || resetForm.newPassword.length < 6) {
    return emit("toast", "⚠️ 新密码至少需要 6 位", "error");
  }
  try {
    const res = await authAPI.resetPassword(
      resetForm.email,
      resetForm.code,
      resetForm.newPassword,
    );
    if (res.data.code === 0) {
      emit("toast", "🎉 密码重置成功！请使用新密码登录", "success");
      // 清空表单
      resetForm.email = "";
      resetForm.code = "";
      resetForm.newPassword = "";
      resetStep.value = 1;
      switchTo("email");
    } else {
      emit("toast", "❌ " + res.data.msg, "error");
    }
  } catch (error) {
    emit(
      "toast",
      "❌ " + (error.response?.data?.msg || "重置失败，请检查验证码"),
      "error",
    );
  }
};
</script>

<style scoped>
/* 样式由父组件的 style.css 提供 */
</style>
