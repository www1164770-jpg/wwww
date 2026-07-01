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
  title: { type: String, default: "正在加载资源..." },
  description: { type: String, default: "" },
});
</script>

<style scoped>
.loading-state {
  display: grid;
  justify-items: center;
  gap: 12px;
  border: 1px dashed #cbd5e1;
  border-radius: var(--radius-card);
  background: #ffffff;
  padding: 38px 24px;
  color: var(--color-muted);
  text-align: center;
}

.spinner {
  width: 30px;
  height: 30px;
  border: 3px solid var(--color-border-soft);
  border-top-color: var(--color-primary);
  border-radius: 999px;
  animation: spin 0.8s linear infinite;
}

strong {
  color: var(--color-heading);
  font-size: 18px;
}

p {
  margin: 0;
  line-height: 1.65;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
