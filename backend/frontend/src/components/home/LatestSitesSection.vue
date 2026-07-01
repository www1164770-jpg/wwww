<template>
  <section class="home-section latest-section">
    <div class="section-title">
      <p>最新</p>
      <h2>最新收录</h2>
      <span>持续整理新上线和新发现的高质量工具网站。</span>
    </div>
    <SiteList
      :sites="sites"
      empty-title="暂无最新收录"
      empty-description="新的工具资源会在收录后展示在这里。"
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
.latest-section {
  display: grid;
  gap: 24px;
  padding: 46px 0 34px;
}

.section-title span {
  color: var(--color-text);
}
</style>
