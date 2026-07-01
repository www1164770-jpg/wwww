<template>
  <section class="home-section hot-section">
    <div class="section-title">
      <p>热门</p>
      <h2>热门推荐</h2>
      <span>近期访问和收藏热度较高的网站资源。</span>
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
  gap: 24px;
  padding: 46px 0 30px;
}

.section-title span {
  color: var(--color-text);
}
</style>
