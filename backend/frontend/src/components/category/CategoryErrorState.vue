<template>
  <div class="category-error-state" role="alert">
    <div class="category-error-state__icon" aria-hidden="true">
      <CircleAlert />
    </div>
    <h2>网站列表加载失败</h2>
    <p>{{ message || "网络或服务暂时不可用，请稍后重试。" }}</p>
    <button type="button" class="btn-primary" :disabled="retrying" @click="$emit('retry')">
      {{ retrying ? "正在重试…" : "重新加载" }}
    </button>
  </div>
</template>

<script setup>
import { CircleAlert } from "lucide-vue-next";

defineProps({
  message: { type: String, default: "" },
  retrying: { type: Boolean, default: false },
});

defineEmits(["retry"]);
</script>

<style scoped>
.category-error-state {
  display: grid;
  min-height: 420px;
  justify-items: center;
  align-content: center;
  gap: 14px;
  padding: 56px 28px;
  border: 1px dashed rgba(239, 91, 69, 0.3);
  border-radius: 20px;
  background: #fffaf8;
  text-align: center;
}

.category-error-state__icon {
  display: grid;
  width: 58px;
  height: 58px;
  place-items: center;
  border-radius: 18px;
  background: #fff1ed;
  color: var(--color-primary-dark);
}

.category-error-state__icon :deep(svg) {
  width: 26px;
  height: 26px;
}

h2 {
  margin: 0;
  color: var(--color-heading);
  font-size: 20px;
  line-height: 1.4;
}

p {
  max-width: 460px;
  margin: 0;
  color: var(--color-muted);
  line-height: 1.75;
}

button {
  min-height: 42px;
  padding: 0 18px;
}

@media (max-width: 640px) {
  .category-error-state {
    min-height: 340px;
    padding: 42px 20px;
  }
}
</style>
