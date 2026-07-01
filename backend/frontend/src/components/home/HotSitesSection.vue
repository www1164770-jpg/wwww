<template>
  <section class="home-section hot-section">
    <div class="section-title">
      <p>热门网站</p>
      <h2>近期更受欢迎的 AI 资源</h2>
      <span>按访问、收藏和推荐热度整理，适合快速发现值得尝试的网站。</span>
    </div>
    <SiteList
      :sites="sites"
      empty-title="暂无热门网站"
      empty-description="热门网站数据加载后会展示在这里。"
      @favorite="$emit('favorite', $event)"
      @visit="$emit('visit', $event)"
    />
  </section>
</template>

<script setup>
import SiteList from "../site/SiteList.vue";
defineProps({ sites: { type: Array, default: () => [] } });
defineEmits(["favorite", "visit"]);
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
</style>
