<template>
  <section v-if="question" class="questionnaire-form" aria-live="polite">
    <header class="progress-head">
      <div><p class="eyebrow">{{ question.stage || '正在了解你的需求' }}</p><h2>帮助我们更懂你</h2></div>
      <span>已完成 {{ progress }}%</span>
    </header>
    <div class="progress-track" aria-hidden="true"><span :style="{ width: `${progress}%` }"></span></div>
    <p class="remaining">预计还需 {{ remainingCount }} 题</p>
    <article class="question-card">
      <p class="question-index">第 {{ questionHistory.length }} 题</p>
      <h3>{{ question.title }}</h3>
      <p v-if="question.description" class="description">{{ question.description }}</p>
      <div class="option-grid" :role="question.type === 'multi' ? 'group' : 'radiogroup'" :aria-label="question.title">
        <button v-for="option in question.options" :key="option.value" type="button" class="option"
          :class="{ selected: isSelected(option.value) }" :role="question.type === 'multi' ? 'checkbox' : 'radio'"
          :aria-checked="isSelected(option.value)" :disabled="submitting" @click="$emit('select', option)">
          {{ option.label }}
        </button>
      </div>
      <p v-if="question.type === 'multi'" class="multi-hint">
        已选择 {{ selectedCount }} 项<span v-if="question.maxSelections">，最多 {{ question.maxSelections }} 项</span>
      </p>
    </article>
    <footer class="actions">
      <button type="button" class="back" :disabled="questionHistory.length <= 1 || submitting" @click="$emit('previous')">上一步</button>
      <button v-if="question.type === 'multi' && !isLastQuestion" type="button" class="finish" :disabled="!canProceed || submitting" @click="$emit('next')">下一步</button>
      <button v-else-if="isLastQuestion" type="button" class="finish" :disabled="!canProceed || submitting" @click="$emit('submit')">{{ submitting ? '正在生成推荐' : '完成并生成推荐' }}</button>
    </footer>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { nextQuestionId } from '../../data/questionnaireConfig';
const props = defineProps({
  question: { type: Object, default: null }, answer: { type: [String, Array], default: '' },
  questionHistory: { type: Array, default: () => [] }, remainingCount: { type: Number, default: 1 },
  submitting: { type: Boolean, default: false }, answers: { type: Object, default: () => ({}) },
});
defineEmits(['select', 'previous', 'submit', 'next']);
const selectedCount = computed(() => Array.isArray(props.answer) ? props.answer.length : (props.answer ? 1 : 0));
const canProceed = computed(() => selectedCount.value >= (props.question?.minSelections || 1));
function isSelected(value) { return Array.isArray(props.answer) ? props.answer.includes(value) : props.answer === value; }
const isLastQuestion = computed(() => {
  if (!props.question || !canProceed.value) return false;
  return !nextQuestionId({ questions: { [props.question.id]: props.question } }, props.question.id, props.answer, props.answers);
});
const progress = computed(() => {
  const answered = props.questionHistory.length - (canProceed.value ? 0 : 1);
  return Math.max(8, Math.min(100, Math.round((answered / Math.max(answered + props.remainingCount, 1)) * 100)));
});
</script>

<style scoped>
.questionnaire-form { display: grid; gap: 18px; }
.progress-head { display: flex; align-items: end; justify-content: space-between; gap: 16px; }
.progress-head h2, .question-card h3 { margin: 0; color: var(--color-heading); }
.progress-head span, .remaining, .eyebrow, .question-index, .description, .multi-hint { color: #718096; }
.eyebrow, .question-index { margin: 0 0 5px; font-size: 13px; font-weight: 800; letter-spacing: .05em; }
.remaining { margin: -10px 0 0; font-size: 14px; }
.progress-track { height: 8px; overflow: hidden; border-radius: 999px; background: #edf2f7; }
.progress-track span { display: block; height: 100%; border-radius: inherit; background: var(--color-primary); transition: width .25s ease; }
.question-card { display: grid; gap: 18px; padding: clamp(22px, 4vw, 34px); border: 1px solid var(--color-border); border-radius: 22px; background: #fff; box-shadow: 0 12px 28px rgba(15,23,42,.04); }
.question-card h3 { font-size: clamp(23px, 3vw, 30px); line-height: 1.35; }
.description { margin: -8px 0 0; }
.option-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 12px; }
.option { min-height: 54px; border: 1px solid var(--color-border); border-radius: 15px; background: #fff; color: var(--color-heading); padding: 12px 15px; text-align: left; font-weight: 750; transition: .18s ease; }
.option:hover, .option:focus-visible { border-color: var(--color-primary); background: var(--color-soft-orange); outline: none; transform: translateY(-1px); }
.option.selected { border-color: var(--color-primary); background: var(--color-primary); color: #fff; }
.actions { display: flex; justify-content: space-between; gap: 12px; }
.actions button { border-radius: var(--radius-pill); padding: 12px 18px; font-weight: 800; }
.back { border: 1px solid var(--color-border); background: #fff; color: #4a5568; }
.finish { border: 0; background: var(--color-primary); color: #fff; }
.finish:disabled, .back:disabled { cursor: not-allowed; opacity: .55; }
@media (max-width: 580px) { .option-grid { grid-template-columns: 1fr; } .progress-head { align-items: start; flex-direction: column; gap: 4px; } }
</style>
