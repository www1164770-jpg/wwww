import { computed, reactive, ref } from "vue";
import { questionnaireAPI, unwrapResponse } from "../../utils/api";
import {
  estimateRemainingQuestions,
  nextQuestionId,
  visibleQuestion,
} from "../../data/questionnaireConfig";

export function useQuestionnaireFlow({ onCompleted } = {}) {
  const config = ref({ questions: {}, start_question_id: "occupation", version: 3 });
  const currentQuestionId = ref("");
  const history = ref([]);
  const answers = reactive({});
  const loading = ref(false);
  const submitting = ref(false);
  const error = ref("");

  const currentQuestion = computed(() =>
    visibleQuestion(config.value, currentQuestionId.value, answers),
  );
  const remainingCount = computed(() =>
    estimateRemainingQuestions(config.value, currentQuestionId.value, answers),
  );

  function clearDownstream(fromIndex) {
    history.value.slice(fromIndex + 1).forEach((id) => delete answers[id]);
    history.value = history.value.slice(0, fromIndex + 1);
  }

  function selectOption(option) {
    if (!currentQuestion.value || submitting.value) return;
    const index = history.value.indexOf(currentQuestionId.value);
    clearDownstream(index);
    if (currentQuestion.value.type === "multi") {
      const selected = Array.isArray(answers[currentQuestionId.value])
        ? [...answers[currentQuestionId.value]] : [];
      const position = selected.indexOf(option.value);
      if (position >= 0) selected.splice(position, 1);
      else if (!currentQuestion.value.maxSelections || selected.length < currentQuestion.value.maxSelections) selected.push(option.value);
      answers[currentQuestionId.value] = selected;
      return;
    }
    answers[currentQuestionId.value] = option.value;
    advance();
  }

  function advance() {
    const question = currentQuestion.value;
    const value = answers[currentQuestionId.value];
    const next = nextQuestionId(config.value, currentQuestionId.value, value, answers);
    if (next) {
      currentQuestionId.value = next;
      if (!history.value.includes(next)) history.value.push(next);
    }
  }

  function goPrevious() {
    if (history.value.length <= 1 || submitting.value) return;
    const leaving = history.value.pop();
    delete answers[leaving];
    currentQuestionId.value = history.value.at(-1);
  }

  function canAdvance() {
    const question = currentQuestion.value;
    const value = answers[currentQuestionId.value];
    if (!question || value == null) return false;
    return question.type !== "multi"
      ? Boolean(value)
      : Array.isArray(value) && value.length >= (question.minSelections || 1);
  }

  function reset() {
    Object.keys(answers).forEach((key) => delete answers[key]);
    history.value = [];
    currentQuestionId.value = "";
    error.value = "";
  }

  async function load() {
    if (loading.value) return;
    loading.value = true;
    error.value = "";
    try {
      const payload = unwrapResponse(await questionnaireAPI.get()) || {};
      config.value = payload;
      Object.assign(answers, payload.initial_answers || {});
      currentQuestionId.value = payload.start_question_id || "occupation";
      history.value = [currentQuestionId.value];
      return payload;
    } catch (requestError) {
      error.value = requestError.response?.data?.msg || "问卷选项加载失败，请稍后重试";
      throw requestError;
    } finally {
      loading.value = false;
    }
  }

  async function submit() {
    if (submitting.value || !canAdvance()) return false;
    submitting.value = true;
    error.value = "";
    try {
      await questionnaireAPI.submit({
        version: config.value.version || 2,
        answers: { ...answers },
      });
      await onCompleted?.();
      return true;
    } catch (requestError) {
      error.value = requestError.response?.data?.msg || "问卷保存失败，请稍后重试";
      throw requestError;
    } finally {
      submitting.value = false;
    }
  }

  return {
    config,
    currentQuestion,
    currentQuestionId,
    history,
    answers,
    loading,
    submitting,
    error,
    remainingCount,
    canAdvance,
    advance,
    load,
    reset,
    selectOption,
    goPrevious,
    submit,
  };
}
