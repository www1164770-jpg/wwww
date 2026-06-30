<template>
  <div class="page">
    <AppHeader />
    <main>
      <h1>{{ currentCategory?.name || "分类详情" }}</h1>
      <SiteFilter
        v-model="filters"
        :categories="children"
        :tags="tags"
        @change="loadSites"
      />
      <LoadingState v-if="loading" text="正在加载网站..." />
      <SiteList
        v-else
        :sites="sites"
        empty-title="该分类暂无网站"
        empty-description="可以尝试切换标签、价格、地区或排序方式。"
        @favorite="favorite"
        @visit="visit"
      />
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
  background: #f8fafc;
}
main {
  display: grid;
  gap: 20px;
  width: min(1180px, calc(100% - 36px));
  margin: 36px auto;
}
</style>
