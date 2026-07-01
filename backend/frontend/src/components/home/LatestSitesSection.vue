<template>
  <section class="home-section latest-section">
    <div class="section-title">
      <p>最新收录</p>
      <h2>新发现的高质量工具</h2>
      <span>持续整理新上线和新发现的 AI 工具、效率站点与创作资源。</span>
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
  gap: 28px;
  padding: 58px 0 48px;
}

.section-title span {
  color: var(--color-text);
  line-height: 1.75;
}
</style>
