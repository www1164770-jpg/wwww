<template>
  <section class="favorite-band">
    <div class="favorite-stack">
      <div class="favorite-copy">
        <p>常用工具栈</p>
        <h2>这些是高频用户真正常用的工具</h2>
        <span>
          根据收藏、点击和评分综合排序，展示最值得优先尝试的网站资源。
        </span>
      </div>

      <div v-if="sites.length" class="favorite-list">
        <button
          v-for="site in sites.slice(0, 6)"
          :key="site.id"
          type="button"
          @click="$emit('visit', site)"
        >
          <strong>{{ site.name }}</strong>
          <small>{{ site.desc || site.description || site.url }}</small>
        </button>
      </div>
      <div v-else class="empty-note">暂无常用工具数据</div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  sites: {
    type: Array,
    default: () => [],
  },
});

defineEmits(["visit"]);
</script>

<style scoped>
.favorite-band {
  margin-top: 46px;
  background: #f1f5f9;
  padding: 90px 0;
}

.favorite-stack {
  display: grid;
  grid-template-columns: minmax(240px, 360px) 1fr;
  gap: 34px;
  width: min(1200px, calc(100% - 40px));
  margin: 0 auto;
}

.favorite-copy p {
  margin: 0 0 10px;
  color: var(--color-primary);
  font-weight: 850;
}

h2 {
  margin: 0 0 14px;
  color: var(--color-heading);
  font-size: clamp(32px, 4vw, 46px);
  line-height: 1.14;
}

.favorite-copy span {
  color: var(--color-text);
  line-height: 1.75;
}

.favorite-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

button,
.empty-note {
  display: grid;
  gap: 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  padding: 18px;
  color: var(--color-heading);
  text-align: left;
  background: #ffffff;
}

button {
  transition:
    transform var(--transition),
    box-shadow var(--transition),
    border-color var(--transition);
}

button:hover {
  border-color: rgba(255, 112, 88, 0.34);
  transform: translateY(-3px);
  box-shadow: var(--shadow-card);
}

small {
  display: -webkit-box;
  overflow: hidden;
  color: var(--color-muted);
  line-height: 1.55;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.empty-note {
  color: var(--color-muted);
}

@media (max-width: 820px) {
  .favorite-stack {
    grid-template-columns: 1fr;
  }

  .favorite-list {
    grid-template-columns: 1fr;
  }
}
</style>
