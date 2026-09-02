<template>
  <div class="loading-state" role="status" aria-live="polite">
    <span class="spinner" aria-hidden="true"></span>
    <strong>{{ text || title || "正在加载资源..." }}</strong>
    <p v-if="description">{{ description }}</p>
  </div>
</template>

<script setup>
defineProps({
  text: { type: String, default: "" },
  title: { type: String, default: "" },
  description: { type: String, default: "" },
});
</script>

<style scoped>
.loading-state {
  display: grid;
  justify-items: center;
  gap: 12px;
  border: 1px dashed var(--app-card-border);
  border-radius: var(--radius-card);
  background: var(--app-panel-soft-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  padding: 42px 24px;
  color: var(--app-text-muted);
  text-align: center;
}

.spinner {
  width: 34px;
  height: 34px;
  border: 3px solid var(--color-border-soft);
  border-top-color: var(--color-primary);
  border-radius: 999px;
  animation: spin 0.8s linear infinite;
}

strong {
  color: var(--app-text-primary);
  font-size: 18px;
}

p {
  max-width: 460px;
  margin: 0;
  line-height: 1.65;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
