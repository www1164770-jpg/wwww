<template>
  <div class="page">
    <AppHeader />
    <main>
      <section class="hero">
        <div>
          <p>我的收藏</p>
          <h1>收藏网站卡片网格</h1>
          <span>集中管理你保存过的 AI 工具和高频资源。</span>
        </div>
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
      </section>

      <LoadingState v-if="loading" text="正在加载收藏..." />
      <SiteList
        v-else
        :sites="filteredFavorites"
        :favorite-ids="favorites.map((site) => site.id)"
        empty-title="暂无收藏"
        empty-description="去首页发现适合你的 AI 工具"
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
  background: #ffffff;
}

main {
  display: grid;
  gap: 24px;
  width: min(1180px, calc(100% - 40px));
  margin: 44px auto 72px;
}

.hero {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  border-radius: var(--radius-large);
  background: linear-gradient(135deg, #ffffff 0%, #fff4f1 100%);
  padding: clamp(28px, 5vw, 58px);
}

.hero p {
  margin: 0 0 8px;
  color: var(--color-primary);
  font-weight: 850;
}

h1 {
  margin: 0 0 10px;
  color: var(--color-heading);
  font-size: clamp(34px, 5vw, 54px);
}

.hero span {
  color: var(--color-text);
}

.filter {
  display: grid;
  gap: 8px;
  width: min(280px, 100%);
  color: var(--color-heading);
  font-weight: 750;
}

select {
  border: 1px solid var(--color-border);
  border-radius: 14px;
  background: #ffffff;
  padding: 12px;
}

@media (max-width: 760px) {
  .hero {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
