<template>
  <section class="home-section recommend-section">
    <div class="section-title">
      <p>{{ loggedIn ? "为你推荐" : "热门推荐" }}</p>
      <h2>
        {{ loggedIn ? "根据你的画像精选工具" : "正在被更多人使用的工具" }}
      </h2>
      <span
        >结合职业、兴趣方向和收藏行为，优先展示更适合你当前任务的资源。</span
      >
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
  gap: 28px;
  padding: 84px 0 38px;
}

.section-title span {
  color: var(--color-text);
  line-height: 1.75;
}
</style>
