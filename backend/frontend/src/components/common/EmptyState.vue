<template>
  <div class="empty-state">
    <strong>{{ title }}</strong>
    <p>{{ description }}</p>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: "No data yet" },
  description: { type: String, default: "Try a different keyword or filter." },
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
