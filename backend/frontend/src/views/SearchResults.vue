<template>
  <div class="page">
    <AppHeader />
    <main>
      <section class="search-hero">
        <h1 v-if="keyword">与“{{ keyword }}”相关的资源</h1>
        <h1 v-else>搜索资源</h1>
        <p>输入工具、网站或使用场景，发现更适合你的资源。</p>
        <SearchBar
          v-model="keyword"
          :navigate-on-submit="false"
          placeholder="搜索 AI 工具、编程开发、设计资源、学习成长..."
          @search="search"
        />
      </section>

      <section class="result-layout">
        <aside class="filter-panel">
          <h2>筛选资源</h2>
          <SiteFilter
            v-model="filters"
            :categories="categories"
            :tags="tags"
            @change="search(keyword)"
          />
        </aside>
        <section class="results-panel">
          <LoadingState v-if="loading" text="正在搜索..." />
          <EmptyState v-else-if="error" title="搜索失败" :description="error" />
          <SiteList
            v-else
            :sites="sites"
            :favorite-pending-ids="favoritePendingIds"
            empty-title="暂无搜索结果"
            empty-description="可以试试“AI工具 / 编程开发 / 设计资源 / 学习成长”"
            @favorite="favorite"
            @visit="visit"
          />
        </section>
      </section>
    </main>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppHeader from "../components/layout/AppHeader.vue";
import EmptyState from "../components/common/EmptyState.vue";
import LoadingState from "../components/common/LoadingState.vue";
import SearchBar from "../components/common/SearchBar.vue";
import SiteFilter from "../components/site/SiteFilter.vue";
import SiteList from "../components/site/SiteList.vue";
import {
  categoryAPI,
  favoriteAPI,
  searchAPI,
  siteAPI,
  tagAPI,
  unwrapResponse,
} from "../utils/api";
import { getAccessToken } from "../utils/auth";
import { errorToast, successToast } from "../utils/toast";

const route = useRoute();
const router = useRouter();
const keyword = ref(route.query.q || "");
const filters = reactive({
  category_id: "",
  tag: "",
  is_free: "",
  region: "",
  sort: route.query.sort || "recommend",
});
const sites = ref([]);
const categories = ref([]);
const tags = ref([]);
const loading = ref(false);
const error = ref("");
const favoritePendingIds = ref([]);

function flattenCategories(value) {
  const source = Array.isArray(value)
    ? value
    : value?.items || value?.categories || [];
  const result = new Map();
  const visit = (item) => {
    if (!item || result.has(item.id)) return;
    result.set(item.id, item);
    (item.children || []).forEach(visit);
  };
  source.forEach(visit);
  return [...result.values()];
}

function listFromResponse(response) {
  const payload = unwrapResponse(response) ?? [];
  return payload.items || payload;
}

async function search(value = keyword.value) {
  const nextValue = value || "";
  keyword.value = nextValue;
  router.replace({
    path: "/search",
    query: { q: nextValue, sort: filters.sort },
  });
  loading.value = true;
  error.value = "";
  try {
    const response = await searchAPI.search({ q: nextValue, ...filters });
    sites.value = listFromResponse(response);
  } catch (err) {
    sites.value = [];
    error.value = err.response?.data?.msg || "搜索失败，请稍后重试";
    errorToast(error.value);
  } finally {
    loading.value = false;
  }
}
async function favorite(site) {
  if (!getAccessToken()) {
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
  await siteAPI.recordClick(site.id).catch(() => {});
  window.open(site.url, "_blank", "noopener,noreferrer");
}
watch(
  () => route.query.q,
  (value) => {
    if (value !== keyword.value) search(value || "");
  },
);
onMounted(async () => {
  try {
    const [categoryRes, tagRes] = await Promise.all([
      categoryAPI.getCategories(),
      tagAPI.getTags(),
    ]);
    categories.value = flattenCategories(unwrapResponse(categoryRes));
    tags.value = unwrapResponse(tagRes) || [];
  } catch {
    errorToast("筛选数据加载失败，请稍后重试");
  }
  await search();
});
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
  margin: 48px auto 78px;
}

.search-hero {
  display: grid;
  justify-items: center;
  gap: 18px;
  border-radius: 24px;
  background:
    radial-gradient(
      circle at 12% 24%,
      rgba(191, 245, 237, 0.34),
      transparent 28%
    ),
    radial-gradient(
      circle at 88% 32%,
      rgba(255, 112, 88, 0.14),
      transparent 30%
    ),
    #ffffff;
  padding: clamp(36px, 5vw, 70px);
  text-align: center;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.04);
}

h1 {
  margin: 0;
  color: var(--color-heading);
  font-size: clamp(38px, 6vw, 60px);
}

.search-hero p {
  margin: 0;
  color: #718096;
  line-height: 1.7;
}

.search-hero :deep(.search-bar) {
  max-width: 780px;
}

.result-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 24px;
  align-items: start;
}

.filter-panel {
  position: sticky;
  top: 92px;
  display: grid;
  gap: 14px;
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

@media (max-width: 900px) {
  .result-layout {
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
