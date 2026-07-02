<template>
  <div class="empty-state">
    <div class="empty-icon" aria-hidden="true">{{ icon }}</div>
    <strong>{{ title }}</strong>
    <p>{{ description }}</p>
    <RouterLink
      v-if="actionText && actionTo"
      class="empty-action"
      :to="actionTo"
    >
      {{ actionText }}
    </RouterLink>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: "暂无数据" },
  description: {
    type: String,
    default: "可以尝试更换关键词或筛选条件",
  },
  actionText: { type: String, default: "" },
  actionTo: { type: [String, Object], default: "" },
  icon: { type: String, default: "◇" },
});
</script>

<style scoped>
.empty-state {
  display: grid;
  justify-items: center;
  gap: 10px;
  border: 1px dashed #cbd5e1;
  border-radius: var(--radius-card);
  background: #ffffff;
  padding: 42px 24px;
  color: var(--color-muted);
  text-align: center;
}

.empty-icon {
  display: grid;
  width: 48px;
  height: 48px;
  place-items: center;
  border-radius: 18px;
  background: var(--color-soft-orange);
  color: var(--color-primary);
  font-size: 22px;
  font-weight: 850;
}

strong {
  display: block;
  color: var(--color-heading);
  font-size: 18px;
}

p {
  max-width: 460px;
  margin: 0;
  line-height: 1.65;
}

.empty-action {
  display: inline-grid;
  min-height: 42px;
  place-items: center;
  border-radius: var(--radius-pill);
  background: var(--color-primary);
  color: #ffffff;
  padding: 0 18px;
  text-decoration: none;
  font-weight: 850;
  box-shadow: 0 14px 28px rgba(255, 112, 88, 0.18);
  transition:
    transform var(--transition),
    background var(--transition),
    box-shadow var(--transition);
}

.empty-action:hover,
.empty-action:focus-visible {
  background: var(--color-primary-dark);
  color: #ffffff;
  transform: translateY(-1px);
  box-shadow: 0 18px 34px rgba(255, 112, 88, 0.24);
  outline: none;
}
</style>
