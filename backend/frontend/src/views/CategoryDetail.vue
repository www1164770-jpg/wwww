<template>
  <div class="page">
    <AppHeader />
    <main>
      <section class="category-hero">
        <p>分类详情</p>
        <h1>{{ currentCategory?.name || "分类详情" }}</h1>
        <span>继续使用现有分类和筛选接口，展示该分类下的网站资源。</span>
      </section>

      <div class="content-layout">
        <aside class="filter-panel">
          <h2>筛选工具</h2>
          <SiteFilter
            v-model="filters"
            :categories="children"
            :tags="tags"
            @change="loadSites"
          />
        </aside>

        <section class="results-panel">
          <LoadingState v-if="loading" text="正在加载网站..." />
          <SiteList
            v-else
            :sites="sites"
            empty-title="该分类暂无网站"
            empty-description="可以尝试切换标签、价格、地区或排序方式。"
            @favorite="favorite"
            @visit="visit"
          />
        </section>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppHeader from "../components/layout/AppHeader.vue";
import LoadingState from "../components/common/LoadingState.vue";
import SiteFilter from "../components/site/SiteFilter.vue";
import SiteList from "../components/site/SiteList.vue";
import { categoryAPI, favoriteAPI, siteAPI, tagAPI } from "../utils/api";

const route = useRoute();
const router = useRouter();
const categories = ref([]);
const tags = ref([]);
const sites = ref([]);
const loading = ref(false);
const filters = reactive({
  category_id: route.params.id,
  tag: "",
  is_free: "",
  region: "",
  sort: "recommend",
});
const currentCategory = computed(() =>
  categories.value.find((item) => String(item.id) === String(route.params.id)),
);
const children = computed(() =>
  categories.value.filter(
    (item) => String(item.parent_id) === String(route.params.id),
  ),
);

async function loadSites(nextFilters = filters) {
  loading.value = true;
  try {
    const response = await siteAPI.getSites({
      ...nextFilters,
      category_id: nextFilters.category_id || route.params.id,
    });
    const payload = response.data?.data ?? response.data ?? {};
    sites.value = payload.items || payload || [];
  } finally {
    loading.value = false;
  }
}
async function favorite(site) {
  if (!localStorage.getItem("access_token")) {
    return router.push({ path: "/login", query: { redirect: route.fullPath } });
  }
  if (site.is_favorited) {
    await favoriteAPI.removeFavorite(site.id);
    site.is_favorited = false;
  } else {
    await favoriteAPI.addFavorite(site.id);
    site.is_favorited = true;
  }
}
async function visit(site) {
  await siteAPI.recordClick(site.id).catch(() => {});
  window.open(site.url, "_blank", "noopener,noreferrer");
}
onMounted(async () => {
  const [categoryRes, tagRes] = await Promise.all([
    categoryAPI.getCategories(),
    tagAPI.getTags(),
  ]);
  categories.value = categoryRes.data?.data || categoryRes.data || [];
  tags.value = tagRes.data?.data || tagRes.data || [];
  await loadSites();
});
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: linear-gradient(180deg, #ffffff 0%, #fffaf8 100%);
}

main {
  display: grid;
  gap: 26px;
  width: min(1180px, calc(100% - 40px));
  margin: 48px auto 78px;
}

.category-hero {
  display: grid;
  gap: 12px;
  border-radius: 24px;
  background:
    radial-gradient(
      circle at 12% 22%,
      rgba(191, 245, 237, 0.32),
      transparent 30%
    ),
    linear-gradient(135deg, #ffffff 0%, #fff4f1 100%);
  padding: clamp(34px, 5vw, 64px);
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.04);
}

.category-hero p {
  margin: 0;
  color: var(--color-primary);
  font-weight: 850;
}

h1 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(36px, 5vw, 56px);
}

.category-hero span {
  color: var(--color-text);
  line-height: 1.7;
}

.content-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 24px;
  align-items: start;
}

.filter-panel {
  position: sticky;
  top: 92px;
  display: grid;
  gap: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: #ffffff;
  padding: 20px;
  box-shadow: var(--shadow-soft);
}

.filter-panel h2 {
  margin: 0;
  color: var(--color-heading);
  font-size: 20px;
}

.filter-panel :deep(.site-filter) {
  grid-template-columns: 1fr;
  border: 0;
  padding: 0;
  box-shadow: none;
}

.results-panel {
  min-width: 0;
}

@media (max-width: 920px) {
  .content-layout {
    grid-template-columns: 1fr;
  }

  .filter-panel {
    position: static;
  }
}
</style>
