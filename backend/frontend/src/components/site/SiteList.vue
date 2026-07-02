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
  <EmptyState
    v-else
    :title="emptyTitle"
    :description="emptyDescription"
    :action-text="emptyActionText"
    :action-to="emptyActionTo"
  />
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
    default: "可以试试 AI 工具、编程开发、设计资源等关键词。",
  },
  emptyActionText: { type: String, default: "" },
  emptyActionTo: { type: [String, Object], default: "" },
});
defineEmits(["favorite", "visit"]);
</script>

<style scoped>
.site-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(270px, 100%), 1fr));
  gap: 20px;
  min-width: 0;
}

@media (max-width: 768px) {
  .site-list {
    grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr));
    gap: 16px;
  }
}
</style>
