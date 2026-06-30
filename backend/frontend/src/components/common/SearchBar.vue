<template>
  <form class="search-bar" @submit.prevent="submit">
    <input v-model.trim="keyword" :placeholder="placeholder" />
    <button type="submit">Search</button>
  </form>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: String, default: "" },
  placeholder: {
    type: String,
    default: "Search AI tools, categories, tags...",
  },
});
const emit = defineEmits(["update:modelValue", "search"]);
const keyword = ref(props.modelValue);

watch(
  () => props.modelValue,
  (value) => {
    keyword.value = value;
  },
);
watch(keyword, (value) => emit("update:modelValue", value));

function submit() {
  emit("search", keyword.value);
}
</script>

<style scoped>
.search-bar {
  display: flex;
  gap: 10px;
  width: 100%;
}
input {
  flex: 1;
  min-width: 0;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 13px 14px;
  font: inherit;
}
button {
  border: 0;
  border-radius: 8px;
  background: #111827;
  color: #fff;
  padding: 0 18px;
  font-weight: 750;
}
</style>
