<template>
  <div ref="root" class="filter-dropdown">
    <span :id="labelId" class="filter-dropdown__label">{{ label }}</span>
    <button
      type="button"
      class="filter-dropdown__trigger"
      :class="{ 'is-open': open }"
      :aria-expanded="open"
      :aria-controls="listboxId"
      :aria-labelledby="`${labelId} ${valueId}`"
      aria-haspopup="listbox"
      @click="toggle"
      @keydown="handleTriggerKeydown"
    >
      <span :id="valueId" class="filter-dropdown__value">{{ selectedLabel }}</span>
      <ChevronDown class="filter-dropdown__chevron" aria-hidden="true" />
    </button>

    <div v-if="open" class="filter-dropdown__menu-wrap">
      <div
        :id="listboxId"
        ref="listbox"
        class="filter-dropdown__menu"
        role="listbox"
        :aria-labelledby="labelId"
        tabindex="-1"
        @keydown="handleListboxKeydown"
      >
        <button
          v-for="(option, index) in options"
          :key="String(option.value)"
          type="button"
          class="filter-dropdown__option"
          :class="{
            'is-selected': isSelected(option),
            'is-active': index === activeIndex,
          }"
          role="option"
          :aria-selected="isSelected(option)"
          @mouseenter="activeIndex = index"
          @click="selectOption(option)"
        >
          <span class="filter-dropdown__check" aria-hidden="true">✓</span>
          <span>{{ option.label }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ChevronDown } from "lucide-vue-next";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: [String, Number], default: "" },
  label: { type: String, required: true },
  options: { type: Array, required: true },
});
const emit = defineEmits(["update:modelValue", "change"]);

const root = ref(null);
const listbox = ref(null);
const open = ref(false);
const activeIndex = ref(0);
const identity = Math.random().toString(36).slice(2, 9);
const labelId = `filter-label-${identity}`;
const valueId = `filter-value-${identity}`;
const listboxId = `filter-listbox-${identity}`;

const selectedIndex = computed(() => {
  const index = props.options.findIndex(
    (option) => String(option.value) === String(props.modelValue),
  );
  return index >= 0 ? index : 0;
});
const selectedLabel = computed(
  () => props.options[selectedIndex.value]?.label || "请选择",
);

function isSelected(option) {
  return String(option.value) === String(props.modelValue);
}

async function show() {
  open.value = true;
  activeIndex.value = selectedIndex.value;
  await nextTick();
  listbox.value?.focus();
  listbox.value
    ?.querySelector(".filter-dropdown__option.is-active")
    ?.scrollIntoView({ block: "nearest" });
}

function close() {
  open.value = false;
}

function toggle() {
  if (open.value) close();
  else void show();
}

function moveActive(offset) {
  const count = props.options.length;
  if (!count) return;
  activeIndex.value = (activeIndex.value + offset + count) % count;
  nextTick(() =>
    listbox.value
      ?.querySelectorAll(".filter-dropdown__option")
      [activeIndex.value]?.scrollIntoView({ block: "nearest" }),
  );
}

function selectOption(option) {
  if (!isSelected(option)) {
    emit("update:modelValue", option.value);
    emit("change", option.value);
  }
  close();
  nextTick(() => root.value?.querySelector("button")?.focus());
}

function selectActive() {
  const option = props.options[activeIndex.value];
  if (option) selectOption(option);
}

function handleTriggerKeydown(event) {
  if (["ArrowDown", "ArrowUp"].includes(event.key)) {
    event.preventDefault();
    if (!open.value) void show();
    else moveActive(event.key === "ArrowDown" ? 1 : -1);
    return;
  }
  if (["Enter", " "].includes(event.key)) {
    event.preventDefault();
    if (open.value) selectActive();
    else void show();
  }
}

function handleListboxKeydown(event) {
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    moveActive(event.key === "ArrowDown" ? 1 : -1);
  } else if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    selectActive();
  } else if (event.key === "Escape") {
    event.preventDefault();
    close();
    nextTick(() => root.value?.querySelector("button")?.focus());
  } else if (event.key === "Tab") {
    close();
  }
}

function handleOutsideClick(event) {
  if (open.value && !root.value?.contains(event.target)) close();
}

watch(() => props.modelValue, () => {
  activeIndex.value = selectedIndex.value;
});
onMounted(() => document.addEventListener("pointerdown", handleOutsideClick));
onBeforeUnmount(() =>
  document.removeEventListener("pointerdown", handleOutsideClick),
);
</script>

<style scoped>
.filter-dropdown {
  position: relative;
  display: grid;
  width: min(230px, 100%);
  gap: 8px;
}

.filter-dropdown__label {
  color: rgba(255, 255, 255, 0.62);
  font-size: 13px;
  font-weight: 500;
}

.filter-dropdown__trigger {
  display: flex;
  width: 100%;
  height: 46px;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.055);
  color: #f1f5f9;
  padding: 0 14px 0 16px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition:
    border-color 180ms ease,
    background 180ms ease,
    box-shadow 180ms ease;
}

.filter-dropdown__trigger:hover {
  border-color: rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.075);
}

.filter-dropdown__trigger:focus-visible,
.filter-dropdown__trigger.is-open {
  border-color: rgba(222, 111, 74, 0.55);
  box-shadow: 0 0 0 3px rgba(222, 111, 74, 0.08);
  outline: none;
}

.filter-dropdown__value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.filter-dropdown__chevron {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
  color: rgba(255, 255, 255, 0.55);
  transition: transform 180ms ease;
}

.filter-dropdown__trigger.is-open .filter-dropdown__chevron {
  transform: rotate(180deg);
}

.filter-dropdown__menu-wrap {
  position: absolute;
  z-index: 50;
  top: calc(100% + 6px);
  left: 0;
  width: 100%;
}

.filter-dropdown__menu {
  max-height: 320px;
  overflow-x: hidden;
  overflow-y: auto;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  background: #181818;
  padding: 6px;
  box-shadow: 0 18px 45px rgba(0, 0, 0, 0.35);
  scrollbar-color: rgba(255, 255, 255, 0.16) transparent;
  scrollbar-width: thin;
}

.filter-dropdown__menu::-webkit-scrollbar {
  width: 6px;
}

.filter-dropdown__menu::-webkit-scrollbar-track {
  background: transparent;
}

.filter-dropdown__menu::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
}

.filter-dropdown__menu::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.25);
}

.filter-dropdown__option {
  display: grid;
  width: 100%;
  min-height: 40px;
  grid-template-columns: 14px minmax(0, 1fr);
  align-items: center;
  gap: 7px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: rgba(255, 255, 255, 0.72);
  padding: 0 12px 0 9px;
  text-align: left;
  font-size: 14px;
  cursor: pointer;
  transition:
    background 150ms ease,
    color 150ms ease;
}

.filter-dropdown__option:hover,
.filter-dropdown__option.is-active {
  background: rgba(255, 255, 255, 0.07);
  color: #ffffff;
  outline: none;
}

.filter-dropdown__option.is-selected {
  background: rgba(222, 111, 74, 0.12);
  color: #f2a083;
}

.filter-dropdown__check {
  visibility: hidden;
  color: #f2a083;
  font-size: 12px;
}

.filter-dropdown__option.is-selected .filter-dropdown__check {
  visibility: visible;
}

@media (max-width: 640px) {
  .filter-dropdown {
    width: 100%;
  }
}
</style>
