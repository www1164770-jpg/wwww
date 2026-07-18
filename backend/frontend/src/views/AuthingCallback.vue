<template>
  <div class="callback-page">
    <section class="callback-panel">
      <RouterLink class="brand" to="/">智汇导航</RouterLink>
      <div>
        <p>正在完成登录...</p>
        <h1>系统正在同步你的账号信息，请稍等。</h1>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { authAPI } from "../utils/api";
import { isValidAuthToken, normalizeAuthSession } from "../utils/auth";
import { useUserStore } from "../stores/user";

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

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

onMounted(async () => {
  const code = String(route.query.code || "");
  if (!code) {
    userStore.logout();
    router.replace("/login?authing_error=invalid_token");
    return;
  }

  try {
    const response = await authAPI.exchange(code);
    const session = normalizeAuthSession(response);
    if (
      !isValidAuthToken(session.access_token) ||
      !session.user_info ||
      !session.user_role
    ) {
      throw new Error("Authing exchange response is incomplete");
    }

    userStore.setLoginSuccess(session);
    const responseData = response.data?.data || {};
    const questionnaireCompleted =
      session.questionnaire_completed === true ||
      session.questionnaire_completed === 1 ||
      session.questionnaire_completed === "1" ||
      session.questionnaire_completed === "true";
    const safeRedirect = normalizeRedirect(responseData.redirect);
    const target = questionnaireCompleted ? safeRedirect : "/questionnaire";
    router.replace(target);
  } catch (error) {
    userStore.logout();
    const errorCode =
      error.response?.status === 503
        ? "authing_exchange_unavailable"
        : "invalid_token";
    router.replace(`/login?authing_error=${errorCode}`);
  }
});
</script>

<style scoped>
.callback-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  background: linear-gradient(180deg, #ffffff 0%, #fffaf8 100%);
  padding: 24px;
}

.callback-panel {
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

p {
  margin: 0 0 6px;
  color: #718096;
  font-weight: 750;
}

h1 {
  margin: 0;
  color: var(--color-heading);
  font-size: 28px;
  line-height: 1.35;
}
</style>
