<template>
  <div class="page">
    <AppHeader />
    <main>
      <h1>{{ currentCategory?.name || "Category" }}</h1>
      <SiteFilter
        v-model="filters"
        :categories="children"
        :tags="tags"
        @change="loadSites"
      />
      <SiteList :sites="sites" @favorite="favorite" @visit="visit" />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppHeader from "../components/layout/AppHeader.vue";
import SiteFilter from "../components/site/SiteFilter.vue";
import SiteList from "../components/site/SiteList.vue";
import { categoryAPI, favoriteAPI, siteAPI, tagAPI } from "../utils/api";

const route = useRoute();
const router = useRouter();
const categories = ref([]);
const tags = ref([]);
const sites = ref([]);
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
  const response = await siteAPI.getSites({
    ...nextFilters,
    category_id: nextFilters.category_id || route.params.id,
  });
  sites.value = response.data?.data?.items || [];
}
async function favorite(site) {
  if (!localStorage.getItem("access_token")) return router.push("/login");
  await favoriteAPI.addFavorite(site.id);
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
  categories.value = categoryRes.data?.data || [];
  tags.value = tagRes.data?.data || [];
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
