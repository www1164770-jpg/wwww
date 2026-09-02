<template>
  <Teleport to="body">
    <div v-if="visible" class="questionnaire-overlay" role="presentation">
      <section class="questionnaire-dialog" role="dialog" aria-modal="true" aria-labelledby="questionnaire-dialog-title">
        <header class="dialog-heading">
          <div>
            <p class="eyebrow">知航屿个性化推荐</p>
            <h2 id="questionnaire-dialog-title">完成你的专属问卷</h2>
          </div>
          <button type="button" class="later" :disabled="flow.submitting.value" @click="$emit('dismiss')">
            稍后填写
          </button>
        </header>
        <p class="dialog-hint">我们会根据你的选择推荐更合适的工具。点击遮罩不会关闭问卷。</p>
        <QuestionnaireForm
          v-if="!flow.loading.value && flow.currentQuestion.value"
          :question="flow.currentQuestion.value"
          :answer="flow.answers[flow.currentQuestionId.value] || ''"
          :answers="flow.answers"
          :question-history="flow.history.value"
          :remaining-count="flow.remainingCount.value"
          :submitting="flow.submitting.value"
          @select="flow.selectOption"
          @previous="flow.goPrevious"
          @next="flow.advance"
          @submit="complete"
        />
        <LoadingState v-else-if="flow.loading.value" text="正在加载问卷…" />
        <p v-if="flow.error.value" class="error" role="alert">{{ flow.error.value }}</p>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { watch } from "vue";
import LoadingState from "../common/LoadingState.vue";
import QuestionnaireForm from "./QuestionnaireForm.vue";
import { useQuestionnaireFlow } from "./useQuestionnaireFlow";
import { useUserStore } from "../../stores/user";
import { errorToast, successToast } from "../../utils/toast";

const props = defineProps({ visible: { type: Boolean, default: false } });
const emit = defineEmits(["dismiss"]);
const userStore = useUserStore();
const flow = useQuestionnaireFlow();

// Opening always starts from a clean path, including after account switching.
watch(
  () => props.visible,
  async (visible) => {
    if (!visible) return;
    flow.reset();
    try {
      await flow.load();
    } catch (error) {
      errorToast(flow.error.value || "问卷加载失败");
    }
  },
  { immediate: true },
);

async function complete() {
  try {
    const saved = await flow.submit();
    if (!saved) return;
    userStore.updateQuestionnaireCompleted(true);
    successToast("问卷保存成功，推荐已更新");
    emit("dismiss");
  } catch (error) {
    errorToast(flow.error.value || "问卷保存失败，请稍后重试");
  }
}
</script>

<style scoped>
.questionnaire-overlay { position: fixed; inset: 0; z-index: 10000; display: grid; place-items: center; padding: 18px; background: rgba(15, 23, 42, .56); backdrop-filter: blur(8px); }
.questionnaire-dialog { width: min(760px, 100%); max-height: calc(100vh - 36px); overflow-y: auto; border: 1px solid var(--mono-border); border-radius: 24px; background: var(--mono-surface, #fff); padding: clamp(22px, 4vw, 36px); box-shadow: 0 24px 70px rgba(15, 23, 42, .22); }
.dialog-heading { display: flex; align-items: start; justify-content: space-between; gap: 18px; margin-bottom: 8px; }
.dialog-heading h2 { margin: 0; color: var(--mono-text, #111); }
.eyebrow { margin: 0 0 5px; color: var(--mono-muted, #718096); font-size: 13px; font-weight: 800; }
.dialog-hint { margin: 0 0 20px; color: var(--mono-muted, #718096); line-height: 1.6; }
.later { border: 1px solid var(--mono-border, #e5e7eb); border-radius: 999px; background: transparent; color: var(--mono-muted, #718096); padding: 9px 13px; white-space: nowrap; }
.later:hover { color: var(--mono-text, #111); background: rgba(17,17,17,.05); }
.error { margin: 14px 0 0; color: #b91c1c; font-weight: 700; }
@media (max-width: 560px) { .dialog-heading { flex-direction: column; } .later { align-self: end; } }
</style>
