<template>
  <aside class="career-selector" aria-labelledby="career-selector-title">
    <header class="career-selector__header">
      <p>职业方向</p>
      <h2 id="career-selector-title">
        {{ activeDirection ? "选择详细职业" : "你目前关注什么方向？" }}
      </h2>
      <span>
        {{
          activeDirection
            ? "选择后，右侧会展示对应的网站工具。"
            : "先选方向，再选择更具体的职业。"
        }}
      </span>
    </header>

    <Transition name="career-panel" mode="out-in">
      <div
        v-if="!activeDirection"
        key="directions"
        class="career-selector__panel"
      >
        <button
          v-for="direction in careerDirections"
          :key="direction.name"
          type="button"
          class="direction-option"
          @click="selectDirection(direction.name)"
        >
          <span>
            <strong>{{ direction.name }}</strong>
            <small>{{ direction.description }}</small>
          </span>
          <b aria-hidden="true">→</b>
        </button>
      </div>

      <div v-else key="occupations" class="career-selector__panel">
        <button
          type="button"
          class="career-selector__back"
          @click="backToDirections"
        >
          <span aria-hidden="true">←</span>
          返回方向
        </button>

        <p class="career-selector__direction">{{ activeDirection }}</p>
        <div class="occupation-options">
          <button
            v-for="occupation in activeOccupations"
            :key="occupation.code"
            type="button"
            class="occupation-option"
            :class="{ 'occupation-option--active': modelValue === occupation.code }"
            :aria-pressed="modelValue === occupation.code"
            @click="selectOccupation(occupation.code)"
          >
            <span>{{ occupation.label }}</span>
            <b aria-hidden="true">
              {{ modelValue === occupation.code ? "✓" : "→" }}
            </b>
          </button>
        </div>
      </div>
    </Transition>
  </aside>
</template>

<script setup>
import { computed, watch } from "vue";
import { careerDirections } from "../../utils/occupation.js";
import { useCareerSelector } from "./useCareerSelector.js";

const props = defineProps({
  modelValue: { type: String, default: "" },
});

const emit = defineEmits(["update:modelValue", "select"]);
const {
  activeDirection,
  backToDirections,
  selectDirection,
  syncWithOccupation,
} = useCareerSelector(props.modelValue);

const activeOccupations = computed(
  () =>
    careerDirections.find(
      (direction) => direction.name === activeDirection.value,
    )?.occupations || [],
);

watch(
  () => props.modelValue,
  (occupation) => {
    if (occupation) syncWithOccupation(occupation);
  },
);

function selectOccupation(occupation) {
  emit("update:modelValue", occupation);
  emit("select", occupation);
}
</script>

<style scoped>
.career-selector {
  min-width: 0;
  overflow: hidden;
  border: 1px solid #e6e8ec;
  border-radius: 24px;
  background: #ffffff;
  padding: 24px;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.07);
}

.career-selector__header {
  display: grid;
  gap: 8px;
  margin-bottom: 20px;
}

.career-selector__header p,
.career-selector__direction {
  margin: 0;
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 850;
}

.career-selector__header h2 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(22px, 2.3vw, 30px);
  line-height: 1.2;
}

.career-selector__header span {
  color: var(--color-muted);
  font-size: 14px;
  line-height: 1.6;
}

.career-selector__panel,
.occupation-options {
  display: grid;
  gap: 10px;
}

.direction-option,
.occupation-option,
.career-selector__back {
  border: 1px solid #e3e6ea;
  background: #ffffff;
  color: var(--color-heading);
  font: inherit;
  cursor: pointer;
}

.direction-option {
  display: flex;
  min-height: 68px;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  border-radius: 16px;
  padding: 13px 15px;
  text-align: left;
  transition:
    border-color 180ms ease,
    background 180ms ease,
    transform 180ms ease;
}

.direction-option span {
  display: grid;
  gap: 3px;
}

.direction-option strong {
  font-size: 15px;
}

.direction-option small {
  color: var(--color-muted);
  line-height: 1.4;
}

.direction-option b,
.occupation-option b {
  color: var(--color-primary);
}

.direction-option:hover,
.direction-option:focus-visible,
.occupation-option:hover,
.occupation-option:focus-visible {
  border-color: var(--color-primary);
  background: var(--color-soft-orange);
  outline: none;
  transform: translateY(-1px);
}

.career-selector__back {
  display: inline-flex;
  width: fit-content;
  min-height: 38px;
  align-items: center;
  gap: 7px;
  border: 0;
  border-radius: var(--radius-pill);
  padding: 0 10px;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 800;
}

.career-selector__back:hover,
.career-selector__back:focus-visible {
  background: var(--color-soft-orange);
  color: var(--color-primary-dark);
  outline: none;
}

.career-selector__direction {
  padding: 4px 2px 2px;
}

.occupation-option {
  display: flex;
  min-height: 48px;
  align-items: center;
  justify-content: space-between;
  border-radius: 14px;
  padding: 0 14px;
  text-align: left;
  transition:
    border-color 180ms ease,
    background 180ms ease,
    color 180ms ease,
    transform 180ms ease;
}

.occupation-option--active {
  border-color: rgba(230, 100, 80, 0.24);
  border-left: 4px solid var(--color-primary);
  background: rgba(230, 100, 80, 0.1);
  color: var(--color-primary-dark);
  padding-left: 10px;
}

.occupation-option--active b {
  color: var(--color-primary-dark);
}

.occupation-option--active:hover,
.occupation-option--active:focus-visible {
  border-color: rgba(230, 100, 80, 0.34);
  border-left-color: var(--color-primary);
  background: rgba(230, 100, 80, 0.14);
  color: var(--color-primary-dark);
}

.career-panel-enter-active,
.career-panel-leave-active {
  transition:
    opacity 200ms ease,
    transform 200ms ease;
}

.career-panel-enter-from {
  opacity: 0;
  transform: translateX(10px);
}

.career-panel-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

@media (prefers-reduced-motion: reduce) {
  .career-panel-enter-active,
  .career-panel-leave-active,
  .direction-option,
  .occupation-option {
    transition: none;
  }
}
</style>
