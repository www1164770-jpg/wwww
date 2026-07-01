<template>
  <section class="home-section recommend-section">
    <div class="section-title">
      <p>{{ loggedIn ? "为你推荐" : "热门推荐" }}</p>
      <h2>{{ loggedIn ? "为你推荐" : "热门推荐" }}</h2>
      <span>根据你的职业、兴趣方向和收藏行为生成推荐。</span>
    </div>
    <SiteList
      :sites="sites"
      empty-title="暂无推荐"
      empty-description="完成问卷或收藏更多工具后，将生成更贴合你的推荐。"
      @favorite="$emit('favorite', $event)"
      @visit="$emit('visit', $event)"
    />
  </section>
</template>

<script setup>
import SiteList from "../site/SiteList.vue";
defineProps({
  sites: { type: Array, default: () => [] },
  loggedIn: { type: Boolean, default: false },
});
defineEmits(["favorite", "visit"]);
</script>

<style scoped>
.recommend-section {
  display: grid;
  gap: 24px;
  padding: 70px 0 30px;
}

.section-title span {
  color: var(--color-text);
  line-height: 1.7;
}
</style>
