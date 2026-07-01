<template>
  <div class="page">
    <AppHeader />
    <main>
      <section class="search-hero">
        <h1>搜索结果</h1>
        <p>输入工具、网站或使用场景，继续调用原有搜索接口获取结果。</p>
        <SearchBar
          v-model="keyword"
          :navigate-on-submit="false"
          @search="search"
        />
      </section>

      <SiteFilter
        v-model="filters"
        :categories="categories"
        :tags="tags"
        @change="search(keyword)"
      />
      <LoadingState v-if="loading" text="正在搜索..." />
      <SiteList
        v-else
        :sites="sites"
        empty-title="没有匹配结果"
        empty-description="没有找到相关网站，可以尝试 AI 工具、编程、设计资源等关键词。"
        @favorite="favorite"
        @visit="visit"
      />
    </main>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppHeader from "../components/layout/AppHeader.vue";
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
} from "../utils/api";

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

async function search(value = keyword.value) {
  const nextValue = value || "";
  keyword.value = nextValue;
  router.replace({
    path: "/search",
    query: { q: nextValue, sort: filters.sort },
  });
  loading.value = true;
  try {
    const response = await searchAPI.search({ q: nextValue, ...filters });
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
watch(
  () => route.query.q,
  (value) => {
    if (value !== keyword.value) search(value || "");
  },
);
onMounted(async () => {
  const [categoryRes, tagRes] = await Promise.all([
    categoryAPI.getCategories(),
    tagAPI.getTags(),
  ]);
  categories.value = categoryRes.data?.data || [];
  tags.value = tagRes.data?.data || [];
  await search();
});
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: linear-gradient(180deg, #ffffff 0%, #fffaf8 100%);
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
  color: var(--color-text);
  line-height: 1.7;
}

.search-hero :deep(.search-bar) {
  max-width: 760px;
}
</style>
