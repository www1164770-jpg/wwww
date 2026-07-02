<template>
  <div class="page">
    <AppHeader />
    <main class="panel">
      <div class="panel-heading">
        <h1>完成职业问卷</h1>
        <p>系统将根据你的职业、兴趣和使用目标推荐更适合的网站资源。</p>
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
    linear-gradient(180deg, #ffffff 0%, #fffaf8 100%);
}

.panel {
  display: grid;
  gap: 30px;
  width: min(980px, calc(100% - 40px));
  margin: 52px auto 78px;
  border: 1px solid var(--color-border);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  padding: clamp(24px, 4vw, 42px);
  box-shadow: var(--shadow-card);
}

.panel-heading {
  display: grid;
  gap: 10px;
  text-align: center;
}

h1 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(34px, 5vw, 52px);
  line-height: 1.12;
}

.panel-heading p {
  max-width: 700px;
  margin: 0 auto;
  color: #718096;
  line-height: 1.7;
}

.error {
  margin: 0;
  color: #b91c1c;
  font-weight: 750;
}

@media (max-width: 768px) {
  .panel {
    width: min(100% - 28px, 980px);
    margin-top: 32px;
  }
}
</style>
