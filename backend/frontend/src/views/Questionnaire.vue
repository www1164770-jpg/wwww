<template>
  <div class="page">
    <AppHeader />
    <main class="panel">
      <div class="panel-heading">
        <AnimatedPageTitle>完成你的专属问卷</AnimatedPageTitle>
        <p>前面的选择会决定后面的题目，我们只询问真正与你相关的内容。</p>
      </div>
      <QuestionnaireForm
        v-if="!loading && tokenValid && currentQuestion"
        :question="currentQuestion"
        :answer="answers[currentQuestion.id] || ''"
        :answers="answers"
        :question-history="history"
        :remaining-count="remainingCount"
        :submitting="submitting"
        @select="selectOption"
        @previous="goPrevious"
        @next="flow.advance"
        @submit="submit"
      />
      <LoadingState v-else-if="loading" text="正在加载问卷…" />
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <div v-if="!loading" class="secondary-actions">
        <button v-if="tokenValid" type="button" class="ghost" @click="skip">暂不填写，返回首页</button>
        <button v-else type="button" class="ghost" @click="relogin">重新登录</button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AnimatedPageTitle from "../components/common/AnimatedPageTitle.vue";
import AppHeader from "../components/layout/AppHeader.vue";
import LoadingState from "../components/common/LoadingState.vue";
import QuestionnaireForm from "../components/questionnaire/QuestionnaireForm.vue";
import { getAccessToken, isValidAuthToken } from "../utils/auth";
import { useUserStore } from "../stores/user";
import { errorToast, successToast } from "../utils/toast";
import { useQuestionnaireFlow } from "../components/questionnaire/useQuestionnaireFlow";

const router = useRouter();
const userStore = useUserStore();
const tokenValid = ref(true);
const flow = useQuestionnaireFlow();
const {
  config, currentQuestionId, history, answers, loading, submitting, error,
  currentQuestion, remainingCount, load, selectOption, goPrevious,
  submit: submitFlow,
} = flow;

async function submit() {
  try {
    await submitFlow();
    userStore.updateQuestionnaireCompleted(true);
    successToast("问卷保存成功，推荐已更新");
    router.replace("/");
  } catch (err) {
    errorToast(error.value);
  }
}

function skip() { router.push("/"); }
function relogin() { userStore.logout(); router.replace("/login"); }

onMounted(async () => {
  tokenValid.value = isValidAuthToken(getAccessToken());
  if (!tokenValid.value) { error.value = "登录状态异常，请重新登录"; return; }
  try {
    await load();
  } catch (err) {
    errorToast(error.value);
  }
});
</script>

<style scoped>
.page { min-height: 100vh; background: linear-gradient(180deg, #fff 0%, #fffaf8 100%); }
.panel { display: grid; gap: 28px; width: min(980px, calc(100% - 40px)); margin: 52px auto 78px; border: 1px solid var(--color-border); border-radius: 24px; background: rgba(255,255,255,.96); padding: clamp(24px,4vw,42px); box-shadow: var(--shadow-card); }
.panel-heading { display: grid; gap: 10px; text-align: center; }
h1 { margin: 0; color: var(--color-heading); font-size: clamp(34px,5vw,52px); line-height: 1.12; }
.panel-heading p { max-width: 700px; margin: 0 auto; color: #718096; line-height: 1.7; }
.error { margin: 0; color: #b91c1c; font-weight: 750; }
.secondary-actions { display: flex; justify-content: center; }
.ghost { border: 1px solid rgba(255,112,88,.34); border-radius: var(--radius-pill); background: #fff; color: var(--color-primary); padding: 12px 18px; font-weight: 850; }
.ghost:hover, .ghost:focus-visible { background: var(--color-soft-orange); color: var(--color-primary-dark); outline: none; }
@media (max-width: 768px) { .panel { width: min(100% - 28px, 980px); margin-top: 32px; } }
</style>
