<template>
  <section class="home-section hot-section">
    <div class="section-title">
      <div class="section-title__row">
        <div>
          <p>热门网站</p>
          <h2>近期更受欢迎的 AI 资源</h2>
        </div>
        <button type="button" :disabled="refreshing" @click="$emit('refresh')">
          {{ refreshing ? "更新中..." : "换一批" }}
        </button>
      </div>
      <span>按访问、收藏和推荐热度整理，适合快速发现值得尝试的网站。</span>
      <small v-if="error">{{ error }}</small>
    </div>
    <SiteList
      :sites="sites"
      empty-title="暂无 AI 资源"
      empty-description="请先在后台添加 AI 工具类网站"
      @visit="$emit('visit', $event)"
    />
  </section>
</template>

<script setup>
import SiteList from "../site/SiteList.vue";
defineProps({
  sites: { type: Array, default: () => [] },
  refreshing: { type: Boolean, default: false },
  error: { type: String, default: "" },
});
defineEmits(["visit", "refresh"]);
</script>

<style scoped>
.hot-section {
  display: grid;
  gap: 28px;
  padding: 58px 0 38px;
}

.section-title span {
  color: var(--color-text);
  line-height: 1.75;
}

.section-title small {
  color: var(--color-primary-dark);
  font-weight: 750;
}

.section-title__row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

button {
  flex: 0 0 auto;
  min-height: 40px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  background: #ffffff;
  color: var(--color-heading);
  padding: 0 16px;
  font-weight: 850;
  transition:
    border-color var(--transition),
    color var(--transition),
    background var(--transition);
}

button:hover,
button:focus-visible {
  border-color: rgba(255, 112, 88, 0.42);
  background: var(--color-soft-orange);
  color: var(--color-primary);
  outline: none;
}

button:disabled {
  cursor: wait;
  opacity: 0.68;
}

@media (max-width: 640px) {
  .section-title__row {
    align-items: stretch;
    flex-direction: column;
  }

  button {
    width: fit-content;
  }
}
</style>
