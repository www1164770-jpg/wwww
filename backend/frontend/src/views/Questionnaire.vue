<template>
  <div class="page">
    <AppHeader />
    <main class="panel">
      <div>
        <p class="eyebrow">Personalization</p>
        <h1>Build your AI resource profile</h1>
      </div>
      <QuestionnaireForm
        :occupations="options.occupations"
        :purposes="options.purposes"
        :interests="options.interests"
        :skill-levels="options.skill_levels"
        :preferences="options.preferences"
        @submit="submit"
      />
      <p v-if="error" class="error">{{ error }}</p>
    </main>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppHeader from "../components/layout/AppHeader.vue";
import QuestionnaireForm from "../components/questionnaire/QuestionnaireForm.vue";
import { questionnaireAPI } from "../utils/api";

const router = useRouter();
const route = useRoute();
const error = ref("");
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
    error.value = err.response?.data?.msg || "Unable to save questionnaire.";
  }
}

onMounted(async () => {
  const response = await questionnaireAPI.get();
  Object.assign(options, dataOf(response));
});
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f8fafc;
}
.panel {
  display: grid;
  gap: 22px;
  width: min(900px, calc(100% - 36px));
  margin: 36px auto;
  padding: 28px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}
.eyebrow {
  margin: 0 0 8px;
  color: #2563eb;
  font-weight: 850;
}
h1 {
  margin: 0;
}
.error {
  color: #b91c1c;
}
</style>
