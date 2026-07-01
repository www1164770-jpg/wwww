<template>
  <div class="page">
    <AppHeader />
    <main class="panel">
      <div class="panel-heading">
        <p class="eyebrow">个性化推荐</p>
        <h1>完善你的 AI 资源画像</h1>
        <span>选择职业、兴趣和偏好后，系统会继续使用原有接口生成推荐。</span>
      </div>
      <QuestionnaireForm
        v-if="!loading"
        :occupations="options.occupations"
        :purposes="options.purposes"
        :interests="options.interests"
        :skill-levels="options.skill_levels"
        :preferences="options.preferences"
        @submit="submit"
      />
      <LoadingState v-else text="正在加载问卷..." />
      <p v-if="error" class="error">{{ error }}</p>
    </main>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppHeader from "../components/layout/AppHeader.vue";
import LoadingState from "../components/common/LoadingState.vue";
import QuestionnaireForm from "../components/questionnaire/QuestionnaireForm.vue";
import { questionnaireAPI } from "../utils/api";

const router = useRouter();
const route = useRoute();
const error = ref("");
const loading = ref(false);
const options = reactive({
  occupations: [],
  purposes: [],
  interests: [],
  skill_levels: [],
  preferences: [],
});

function dataOf(response) {
  return response?.data?.data ?? {};
}

async function submit(form) {
  try {
    await questionnaireAPI.submit(form);
    localStorage.setItem("questionnaire_completed", "true");
    router.push(route.query.redirect || "/");
  } catch (err) {
    error.value = err.response?.data?.msg || "问卷保存失败，请稍后重试";
  }
}

onMounted(async () => {
  loading.value = true;
  try {
    const response = await questionnaireAPI.get();
    Object.assign(options, dataOf(response));
  } catch (err) {
    error.value = err.response?.data?.msg || "问卷选项加载失败，请稍后重试";
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.page {
  min-height: 100vh;
  background:
    radial-gradient(
      circle at 12% 18%,
      rgba(191, 245, 237, 0.36),
      transparent 28%
    ),
    radial-gradient(
      circle at 88% 28%,
      rgba(255, 112, 88, 0.16),
      transparent 30%
    ),
    #ffffff;
}

.panel {
  display: grid;
  gap: 28px;
  width: min(920px, calc(100% - 40px));
  margin: 48px auto 72px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-large);
  background: rgba(255, 255, 255, 0.94);
  padding: clamp(24px, 4vw, 40px);
  box-shadow: var(--shadow-card);
}

.panel-heading {
  display: grid;
  gap: 10px;
  text-align: center;
}

.eyebrow {
  color: var(--color-primary);
}

h1 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(34px, 5vw, 52px);
  line-height: 1.12;
}

.panel-heading span {
  color: var(--color-text);
  line-height: 1.7;
}

.error {
  margin: 0;
  color: #b91c1c;
  font-weight: 750;
}
</style>
