<template>
  <div v-if="sites.length" class="site-list">
    <SiteCard
      v-for="site in sites"
      :key="site.id"
      :site="site"
      :favorited="Boolean(site.is_favorited) || favoriteIds.includes(site.id)"
      @favorite="$emit('favorite', $event)"
      @visit="$emit('visit', $event)"
    />
  </div>
  <EmptyState v-else :title="emptyTitle" :description="emptyDescription" />
</template>

<script setup>
import EmptyState from "../common/EmptyState.vue";
import SiteCard from "./SiteCard.vue";

defineProps({
  sites: { type: Array, default: () => [] },
  favoriteIds: { type: Array, default: () => [] },
  emptyTitle: { type: String, default: "暂无网站" },
  emptyDescription: {
    type: String,
    default: "可以尝试 AI 工具、编程、设计资源等关键词。",
  },
});
defineEmits(["favorite", "visit"]);
</script>

<style scoped>
.site-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(270px, 1fr));
  gap: 20px;
}
</style>
