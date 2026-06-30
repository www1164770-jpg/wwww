<template>
  <div class="page">
    <AppHeader />
    <main>
      <h1>我的收藏</h1>
      <label class="filter">
        分类
        <select v-model="selectedCategory">
          <option value="">全部分类</option>
          <option
            v-for="category in categories"
            :key="category.id || category.name"
            :value="String(category.id || category.name)"
          >
            {{ category.name }}
          </option>
        </select>
      </label>
      <LoadingState v-if="loading" text="正在加载收藏..." />
      <SiteList
        v-else
        :sites="filteredFavorites"
        :favorite-ids="favorites.map((site) => site.id)"
        empty-title="暂无收藏"
        empty-description="收藏实用网站后，会在这里集中展示。"
        @favorite="remove"
        @visit="visit"
      />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import AppHeader from "../components/layout/AppHeader.vue";
import LoadingState from "../components/common/LoadingState.vue";
import SiteList from "../components/site/SiteList.vue";
import { categoryAPI, favoriteAPI, siteAPI } from "../utils/api";

const favorites = ref([]);
const categories = ref([]);
const selectedCategory = ref("");
const loading = ref(false);
const filteredFavorites = computed(() => {
  if (!selectedCategory.value) return favorites.value;
  return favorites.value.filter((site) => {
    const id = site.category_id ?? site.category?.id ?? site.category_name;
    return String(id) === selectedCategory.value;
  });
});

async function load() {
  loading.value = true;
  try {
    const [favoriteRes, categoryRes] = await Promise.all([
      favoriteAPI.getFavorites(),
      categoryAPI.getCategories().catch(() => ({ data: { data: [] } })),
    ]);
    const payload = favoriteRes.data?.data ?? favoriteRes.data ?? [];
    favorites.value = payload.items || payload || [];
    categories.value = categoryRes.data?.data || categoryRes.data || [];
  } finally {
    loading.value = false;
  }
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
.filter {
  display: grid;
  gap: 8px;
  width: min(280px, 100%);
  color: #374151;
  font-weight: 750;
}
select {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  padding: 10px;
}
</style>
