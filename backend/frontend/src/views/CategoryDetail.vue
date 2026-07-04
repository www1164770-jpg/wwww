<template>
  <div class="page">
    <AppHeader />
    <main>
      <section class="category-hero">
        <h1>{{ currentCategory?.name || "分类详情" }}</h1>
        <p>
          {{
            currentCategory?.description ||
            "按标签、价格、地区和排序方式筛选该分类下的网站资源。"
          }}
        </p>
      </section>

      <div class="content-layout">
        <aside class="filter-panel">
          <h2>筛选条件</h2>
          <SiteFilter
            v-model="filters"
            :categories="children"
            :tags="tags"
            @change="loadSites"
          />
        </aside>

        <section class="results-panel">
          <LoadingState v-if="loading" text="正在加载网站..." />
          <div v-else-if="sites.length" class="category-site-grid">
            <SiteCard
              v-for="site in sites"
              :key="site.id || site.url || site.name"
              :site="site"
              :favorited="Boolean(site.is_favorited)"
              :favorite-pending="favoritePendingIds.includes(site.id)"
              @favorite="favorite"
              @visit="visit"
            />
          </div>
          <EmptyState
            v-else
            :title="error ? '资源加载失败' : '暂无该分类的网站资源'"
            :description="
              error ||
              '可以先在后台为该分类添加网站信息，页面会优先展示匹配的兜底资源。'
            "
          />
        </section>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppHeader from "../components/layout/AppHeader.vue";
import LoadingState from "../components/common/LoadingState.vue";
import EmptyState from "../components/common/EmptyState.vue";
import SiteFilter from "../components/site/SiteFilter.vue";
import SiteCard from "../components/site/SiteCard.vue";
import {
  categoryAPI,
  favoriteAPI,
  getCategoryFallbackSites,
  normalizeUrl,
  siteAPI,
  tagAPI,
  unwrapList,
} from "../utils/api";
import { errorToast, successToast } from "../utils/toast";

const route = useRoute();
const router = useRouter();
const categories = ref([]);
const tags = ref([]);
const sites = ref([]);
const loading = ref(false);
const error = ref("");
const favoritePendingIds = ref([]);
const filters = reactive({
  category_id: "",
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

function flattenCategories(value) {
  const source = Array.isArray(value) ? value : value?.items || value || [];
  const result = new Map();
  const visit = (item) => {
    if (!item || result.has(item.id)) return;
    result.set(item.id, item);
    (item.children || []).forEach(visit);
  };
  source.forEach(visit);
  return [...result.values()];
}

function normalizeList(value) {
  return Array.isArray(value) ? value.filter(Boolean) : [];
}

function withFallbackSites(items) {
  const realSites = normalizeList(items);
  if (realSites.length) return realSites;
  return getCategoryFallbackSites(currentCategory.value);
}

function cleanFilters(source = {}) {
  const params = {
    category_id: route.params.id,
    page: 1,
    page_size: 12,
    limit: 12,
    sort: source.sort || "recommend",
    tag: source.tag,
    is_free: source.is_free,
    region: source.region,
  };
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== "" && value != null),
  );
}

async function loadSites(nextFilters = filters) {
  loading.value = true;
  error.value = "";
  try {
    const response = await siteAPI.getSites(cleanFilters(nextFilters));
    sites.value = withFallbackSites(unwrapList(response));
  } catch (err) {
    error.value = err.response?.data?.msg || "网站加载失败，请稍后重试";
    sites.value = withFallbackSites([]);
    errorToast(error.value);
  } finally {
    loading.value = false;
  }
}
async function favorite(site) {
  if (!localStorage.getItem("access_token")) {
    return router.push({ path: "/login", query: { redirect: route.fullPath } });
  }
  if (favoritePendingIds.value.includes(site.id)) return;
  const wasFavorited = Boolean(site.is_favorited);
  favoritePendingIds.value = [...favoritePendingIds.value, site.id];
  try {
    if (wasFavorited) {
      await favoriteAPI.removeFavorite(site.id);
      site.is_favorited = false;
      successToast("已取消收藏");
    } else {
      await favoriteAPI.addFavorite(site.id);
      site.is_favorited = true;
      successToast("已收藏");
    }
  } catch {
    site.is_favorited = wasFavorited;
    errorToast("操作失败，请稍后重试");
  } finally {
    favoritePendingIds.value = favoritePendingIds.value.filter(
      (id) => id !== site.id,
    );
  }
}
async function visit(site) {
  const url = normalizeUrl(site?.url);
  if (site?.id && !site.external_only) {
    await siteAPI.recordClick(site.id).catch(() => {});
  }
  if (url) {
    window.open(url, "_blank", "noopener,noreferrer");
  } else if (site?.id && !site.external_only) {
    router.push(`/site/${site.id}`);
  }
}
onMounted(async () => {
  try {
    const [categoryRes, tagRes] = await Promise.all([
      categoryAPI.getCategories(),
      tagAPI.getTags(),
    ]);
    categories.value = flattenCategories(unwrapList(categoryRes));
    tags.value = unwrapList(tagRes);
  } catch (err) {
    error.value = err.response?.data?.msg || "筛选数据加载失败，请稍后重试";
    errorToast(error.value);
  }
  await loadSites();
});

watch(
  () => route.params.id,
  async () => {
    filters.category_id = "";
    await loadSites();
  },
);
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #ffffff;
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

h1 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(36px, 5vw, 56px);
}

.category-hero p {
  max-width: 720px;
  margin: 0;
  color: #718096;
  line-height: 1.7;
}

.content-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
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

.category-site-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(260px, 100%), 1fr));
  gap: 20px;
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

@media (max-width: 768px) {
  main {
    width: min(100% - 28px, 1180px);
    margin-top: 32px;
  }
}
</style>
