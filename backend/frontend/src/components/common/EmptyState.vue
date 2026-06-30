<template>
  <div class="empty-state">
    <strong>{{ title }}</strong>
    <p>{{ description }}</p>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: "暂无数据" },
  description: { type: String, default: "可以尝试更换关键词或筛选条件。" },
});
</script>

<style scoped>
.empty-state {
  padding: 34px;
  text-align: center;
  color: #6b7280;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #f9fafb;
}
strong {
  display: block;
  color: #111827;
  margin-bottom: 8px;
}
p {
  margin: 0;
}
</style>
