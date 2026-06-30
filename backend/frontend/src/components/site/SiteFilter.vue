<template>
  <div class="site-filter">
    <select v-model="local.category_id" @change="emitChange">
      <option value="">All categories</option>
      <option
        v-for="category in categories"
        :key="category.id"
        :value="category.id"
      >
        {{ category.name }}
      </option>
    </select>
    <select v-model="local.tag" @change="emitChange">
      <option value="">All tags</option>
      <option v-for="tag in tags" :key="tag.id || tag.name" :value="tag.name">
        {{ tag.name }}
      </option>
    </select>
    <select v-model="local.is_free" @change="emitChange">
      <option value="">Free and paid</option>
      <option value="free">Free</option>
      <option value="paid">Paid</option>
    </select>
    <select v-model="local.region" @change="emitChange">
      <option value="">All regions</option>
      <option value="domestic">Domestic</option>
      <option value="international">International</option>
    </select>
    <select v-model="local.sort" @change="emitChange">
      <option value="recommend">Recommended</option>
      <option value="hot">Hot</option>
      <option value="latest">Latest</option>
      <option value="rating">Rating</option>
    </select>
  </div>
</template>

<script setup>
import { reactive, watch } from "vue";

const props = defineProps({
  modelValue: { type: Object, default: () => ({}) },
  categories: { type: Array, default: () => [] },
  tags: { type: Array, default: () => [] },
});
const emit = defineEmits(["update:modelValue", "change"]);
const local = reactive({
  category_id: "",
  tag: "",
  is_free: "",
  region: "",
  sort: "recommend",
});

watch(
  () => props.modelValue,
  (value) => Object.assign(local, value || {}),
  { immediate: true, deep: true },
);

function emitChange() {
  const payload = { ...local };
  emit("update:modelValue", payload);
  emit("change", payload);
}
</script>

<style scoped>
.site-filter {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}
select {
  min-width: 0;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px;
  background: #fff;
}
@media (max-width: 900px) {
  .site-filter {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
