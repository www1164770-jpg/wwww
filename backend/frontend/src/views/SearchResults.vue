<template>
  <div class="page">
    <AppHeader />
    <main>
      <h1>Search</h1>
      <SearchBar v-model="keyword" :navigate-on-submit="false" @search="search" />
      <SiteFilter
        v-model="filters"
        :categories="categories"
        :tags="tags"
        @change="search(keyword)"
      />
      <LoadingState
        v-if="loading"
        title="Searching"
        description="Looking for matching AI resources."
      />
      <SiteList
        v-else
        :sites="sites"
        empty-title="No matching sites"
        empty-description="No related sites found. Try AI tools, programming, or design resources."
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
  if (!localStorage.getItem("access_token")) return router.push("/login");
  await favoriteAPI.addFavorite(site.id);
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
  background: #f8fafc;
}
main {
  display: grid;
  gap: 20px;
  width: min(1180px, calc(100% - 36px));
  margin: 36px auto;
}
</style>
