<template>
  <section class="home-section">
    <div class="section-title">
      <p>Fresh</p>
      <h2>Latest additions</h2>
    </div>
    <SiteList
      :sites="sites"
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
.home-section {
  display: grid;
  gap: 18px;
}
.section-title p {
  margin: 0 0 6px;
  color: #2563eb;
  font-weight: 800;
}
.section-title h2 {
  margin: 0;
}
</style>
