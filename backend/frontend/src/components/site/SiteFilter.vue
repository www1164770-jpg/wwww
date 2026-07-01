<template>
  <div class="site-filter">
    <select v-model="local.category_id" @change="emitChange">
      <option value="">全部分类</option>
      <option
        v-for="category in categories"
        :key="category.id"
        :value="category.id"
      >
        {{ category.name }}
      </option>
    </select>
    <select v-model="local.tag" @change="emitChange">
      <option value="">全部标签</option>
      <option v-for="tag in tags" :key="tag.id || tag.name" :value="tag.name">
        {{ tag.name }}
      </option>
    </select>
    <select v-model="local.is_free" @change="emitChange">
      <option value="">免费和付费</option>
      <option value="free">免费</option>
      <option value="paid">付费</option>
    </select>
    <select v-model="local.region" @change="emitChange">
      <option value="">全部地区</option>
      <option value="domestic">国内</option>
      <option value="international">国外</option>
    </select>
    <select v-model="local.sort" @change="emitChange">
      <option value="recommend">推荐排序</option>
      <option value="hot">热度最高</option>
      <option value="latest">最新收录</option>
      <option value="rating">评分最高</option>
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
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #ffffff;
  padding: 14px;
  box-shadow: var(--shadow-soft);
}

select {
  min-width: 0;
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: #ffffff;
  color: var(--color-heading);
  padding: 12px;
}

@media (max-width: 900px) {
  .site-filter {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .site-filter {
    grid-template-columns: 1fr;
  }
}
</style>
