<template>
  <form class="search-bar" @submit.prevent="submit">
    <input v-model.trim="keyword" :placeholder="placeholder" />
    <button type="submit" aria-label="搜索">搜索</button>
  </form>
</template>

<script setup>
import { ref, watch } from "vue";
import { useRouter } from "vue-router";

const props = defineProps({
  modelValue: { type: String, default: "" },
  placeholder: {
    type: String,
    default: "搜索 AI 工具、分类、标签...",
  },
  navigateOnSubmit: { type: Boolean, default: true },
});
const emit = defineEmits(["update:modelValue", "search"]);
const router = useRouter();
const keyword = ref(props.modelValue);

watch(
  () => props.modelValue,
  (value) => {
    keyword.value = value;
  },
);
watch(keyword, (value) => emit("update:modelValue", value));

function submit() {
  const value = keyword.value.trim();
  emit("search", value);
  if (props.navigateOnSubmit && value) {
    router.push({ path: "/search", query: { q: value } });
  }
}
</script>

<style scoped>
.search-bar {
  display: grid;
  grid-template-columns: 1fr auto;
  width: 100%;
  min-height: 60px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: #ffffff;
  box-shadow: var(--shadow-soft);
  transition:
    border-color var(--transition),
    box-shadow var(--transition);
}

.search-bar:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 16px 36px rgba(255, 112, 88, 0.14);
}

input {
  min-width: 0;
  border: 0;
  background: transparent;
  padding: 0 8px 0 22px;
  outline: 0;
}

button {
  align-self: center;
  width: 48px;
  height: 48px;
  min-width: 48px;
  margin-right: 6px;
  border: 0;
  border-radius: 50%;
  background: var(--color-primary);
  color: #ffffff;
  font-size: 0;
  box-shadow: 0 12px 24px rgba(255, 112, 88, 0.2);
}

button::before {
  content: "";
  display: block;
  width: 16px;
  height: 16px;
  margin: 0 auto;
  border: 2px solid currentColor;
  border-radius: 50%;
  box-shadow: 8px 8px 0 -6px currentColor;
  transform: rotate(-15deg);
}
</style>
