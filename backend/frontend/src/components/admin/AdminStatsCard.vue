<template>
  <article class="stats-card">
    <span>{{ label }}</span>
    <strong>{{ value ?? 0 }}</strong>
  </article>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [Number, String], default: 0 },
});
</script>

<style scoped>
.stats-card {
  display: grid;
  gap: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
  padding: 16px;
}
span {
  color: #6b7280;
  font-size: 13px;
  font-weight: 750;
}
strong {
  color: #111827;
  font-size: 30px;
}
</style>
