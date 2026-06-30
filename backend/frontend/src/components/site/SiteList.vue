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
  emptyTitle: { type: String, default: "No sites found" },
  emptyDescription: {
    type: String,
    default: "Try AI tools, programming, or design resources.",
  },
});
defineEmits(["favorite", "visit"]);
</script>

<style scoped>
.site-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
</style>
