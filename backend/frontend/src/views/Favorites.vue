<template>
  <div class="page">
    <AppHeader />
    <main>
      <h1>My favorites</h1>
      <SiteList
        :sites="favorites"
        empty-title="No favorites yet"
        empty-description="Collect useful sites and add notes for later."
        @favorite="remove"
        @visit="visit"
      />
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import AppHeader from "../components/layout/AppHeader.vue";
import SiteList from "../components/site/SiteList.vue";
import { favoriteAPI, siteAPI } from "../utils/api";

const favorites = ref([]);

async function load() {
  const response = await favoriteAPI.getFavorites();
  favorites.value = Array.isArray(response.data?.data)
    ? response.data.data
    : [];
}
async function remove(site) {
  await favoriteAPI.removeFavorite(site.id);
  favorites.value = favorites.value.filter((item) => item.id !== site.id);
}
async function visit(site) {
  await siteAPI.recordClick(site.id).catch(() => {});
  window.open(site.url, "_blank", "noopener,noreferrer");
}
onMounted(load);
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #f8fafc;
}
main {
  display: grid;
  gap: 20px;
  width: min(1180px, calc(100% - 36px));
  margin: 36px auto;
}
</style>
