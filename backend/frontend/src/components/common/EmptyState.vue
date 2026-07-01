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
  border: 1px dashed #cbd5e1;
  border-radius: var(--radius-card);
  background: #ffffff;
  padding: 38px 24px;
  color: var(--color-muted);
  text-align: center;
}

strong {
  display: block;
  margin-bottom: 8px;
  color: var(--color-heading);
  font-size: 18px;
}

p {
  margin: 0;
  line-height: 1.65;
}
</style>
