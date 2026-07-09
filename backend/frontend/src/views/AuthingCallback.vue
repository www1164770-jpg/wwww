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
import { storeUserSessionFromPayload, userAPI } from "../utils/api";

const route = useRoute();
const router = useRouter();

function normalizeRedirect(path) {
  if (!path || !String(path).startsWith("/") || String(path).startsWith("//")) {
    return "/";
  }
  return String(path);
}

function isValidToken(token) {
  const value = String(token || "");
  if (value.length <= 20) return false;
  return !value.includes(".") || value.split(".").length === 3;
}

function clearAuthStorage() {
  localStorage.removeItem("token");
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("questionnaire_completed");
  localStorage.removeItem("is_logged_in");
}

onMounted(async () => {
  const token = route.query.token;
  const questionnaireCompleted = route.query.questionnaire_completed === "1";
  const redirect = normalizeRedirect(route.query.redirect);

  if (!isValidToken(token)) {
    clearAuthStorage();
    router.replace("/login?authing_error=invalid_token");
    return;
  }

  storeUserSessionFromPayload(
    { token, questionnaire_completed: questionnaireCompleted },
    { token, questionnaireCompleted },
  );

  try {
    const profileResponse = await userAPI.getProfile();
    storeUserSessionFromPayload(profileResponse, {
      token,
      questionnaireCompleted,
    });
  } catch {
    localStorage.setItem(
      "questionnaire_completed",
      questionnaireCompleted ? "true" : "false",
    );
  }

  router.replace(questionnaireCompleted ? redirect : "/questionnaire");
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
