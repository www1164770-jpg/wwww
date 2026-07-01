<template>
  <div class="page">
    <AppHeader />
    <main>
      <HeroSearch v-model="keyword" @search="goSearch(keyword)" />
      <ToolMarquee />
      <CategorySection :categories="categories" />
      <CareerRecommend
        :active-career="activeCareer"
        @select-career="selectCareer"
      />
      <RecommendSection
        :sites="recommended"
        :logged-in="loggedIn"
        @favorite="toggleFavorite"
        @visit="visitSite"
      />
      <HotSitesSection
        :sites="hotSites"
        @favorite="toggleFavorite"
        @visit="visitSite"
      />
      <LatestSitesSection
        :sites="latestSites"
        @favorite="toggleFavorite"
        @visit="visitSite"
      />
      <FavoriteStack :sites="hotSites" @visit="visitSite" />
    </main>
    <AppFooter />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppFooter from "../components/layout/AppFooter.vue";
import AppHeader from "../components/layout/AppHeader.vue";
import CareerRecommend from "../components/home/CareerRecommend.vue";
import CategorySection from "../components/home/CategorySection.vue";
import FavoriteStack from "../components/home/FavoriteStack.vue";
import HeroSearch from "../components/home/HeroSearch.vue";
import HotSitesSection from "../components/home/HotSitesSection.vue";
import LatestSitesSection from "../components/home/LatestSitesSection.vue";
import RecommendSection from "../components/home/RecommendSection.vue";
import ToolMarquee from "../components/home/ToolMarquee.vue";
import { categoryAPI, favoriteAPI, siteAPI } from "../utils/api";

const router = useRouter();
const keyword = ref("");
const activeCareer = ref("");
const categories = ref([]);
const recommended = ref([]);
const hotSites = ref([]);
const latestSites = ref([]);
const loggedIn = computed(() => Boolean(localStorage.getItem("access_token")));

function payload(response, fallback = []) {
  return response?.data?.data ?? fallback;
}

function goSearch(value) {
  router.push({ path: "/search", query: { q: value || "" } });
}

function selectCareer(career) {
  activeCareer.value = career;
}

async function visitSite(site) {
  try {
    await siteAPI.recordClick(site.id);
  } catch {
    // click logging should not block navigation
  }
  window.open(site.url, "_blank", "noopener,noreferrer");
}

async function toggleFavorite(site) {
  if (!loggedIn.value) {
    router.push({ path: "/login", query: { redirect: "/" } });
    return;
  }
  if (site.is_favorited) {
    await favoriteAPI.removeFavorite(site.id);
    site.is_favorited = false;
  } else {
    await favoriteAPI.addFavorite(site.id);
    site.is_favorited = true;
  }
}

async function loadHome() {
  const [categoryRes, recommendRes, hotRes, latestRes] =
    await Promise.allSettled([
      categoryAPI.getCategories(),
      loggedIn.value
        ? siteAPI.getRecommend({ limit: 8 })
        : siteAPI.getHot({ limit: 8 }),
      siteAPI.getHot({ limit: 8 }),
      siteAPI.getLatest({ limit: 8 }),
    ]);
  categories.value = payload(categoryRes.value, [])
    .filter((item) => !item.parent_id)
    .slice(0, 8);
  recommended.value = payload(recommendRes.value, []);
  hotSites.value = payload(hotRes.value, []);
  latestSites.value = payload(latestRes.value, []);
}

onMounted(loadHome);
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #ffffff;
}

main {
  display: grid;
  gap: 0;
}
</style>
