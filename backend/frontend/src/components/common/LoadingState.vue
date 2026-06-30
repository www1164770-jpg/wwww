<template>
  <div class="loading-state" role="status" aria-live="polite">
    <span class="spinner" aria-hidden="true"></span>
    <strong>{{ text || title }}</strong>
    <p v-if="description">{{ description }}</p>
  </div>
</template>

<script setup>
defineProps({
  text: { type: String, default: "" },
  title: { type: String, default: "正在加载..." },
  description: { type: String, default: "" },
});
</script>

<style scoped>
.loading-state {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 34px;
  text-align: center;
  color: #6b7280;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}
.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #e5e7eb;
  border-top-color: #111827;
  border-radius: 999px;
  animation: spin 0.8s linear infinite;
}
strong {
  color: #111827;
}
p {
  margin: 0;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
