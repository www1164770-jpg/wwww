<template>
  <div class="page">
    <AppHeader />

    <main class="home-main">
      <HeroSearch v-model="keyword" @search="goSearch(keyword)" />
      <ToolMarquee />

      <div v-if="loading || error" class="home-state">
        <LoadingState v-if="loading" />
        <EmptyState v-else title="首页数据加载失败" :description="error" />
      </div>

      <template v-else>
        <section id="categories">
          <CategorySection :categories="categories" />
        </section>

        <section id="career">
          <CareerRecommend @select-career="goSearch" />
        </section>

        <section id="recommend">
          <RecommendSection
            :sites="recommended"
            :logged-in="loggedIn"
            @favorite="toggleFavorite"
            @visit="visitSite"
          />
        </section>

        <section id="hot">
          <HotSitesSection
            :sites="hotSites"
            @favorite="toggleFavorite"
            @visit="visitSite"
          />
        </section>

        <section id="latest">
          <LatestSitesSection
            :sites="latestSites"
            @favorite="toggleFavorite"
            @visit="visitSite"
          />
        </section>

        <section id="favorite-stack">
          <FavoriteStack :sites="hotSites" @visit="visitSite" />
        </section>
      </template>
    </main>

    <AppFooter />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import EmptyState from "../components/common/EmptyState.vue";
import LoadingState from "../components/common/LoadingState.vue";
import CareerRecommend from "../components/home/CareerRecommend.vue";
import CategorySection from "../components/home/CategorySection.vue";
import FavoriteStack from "../components/home/FavoriteStack.vue";
import HeroSearch from "../components/home/HeroSearch.vue";
import HotSitesSection from "../components/home/HotSitesSection.vue";
import LatestSitesSection from "../components/home/LatestSitesSection.vue";
import RecommendSection from "../components/home/RecommendSection.vue";
import ToolMarquee from "../components/home/ToolMarquee.vue";
import AppFooter from "../components/layout/AppFooter.vue";
import AppHeader from "../components/layout/AppHeader.vue";
import { categoryAPI, favoriteAPI, siteAPI } from "../utils/api";

const router = useRouter();
const keyword = ref("");
const categories = ref([]);
const recommended = ref([]);
const hotSites = ref([]);
const latestSites = ref([]);
const loading = ref(false);
const error = ref("");
const loggedIn = computed(() => Boolean(localStorage.getItem("access_token")));

function payload(response, fallback = []) {
  return response?.data?.data ?? fallback;
}

function goSearch(value) {
  router.push({ path: "/search", query: { q: value || "" } });
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
  loading.value = true;
  error.value = "";
  try {
    const [categoryRes, recommendRes, hotRes, latestRes] =
      await Promise.allSettled([
        categoryAPI.getCategories(),
        loggedIn.value
          ? siteAPI.getRecommend({ limit: 8 })
          : siteAPI.getHot({ limit: 8 }),
        siteAPI.getHot({ limit: 8 }),
        siteAPI.getLatest({ limit: 8 }),
      ]);

    const failed = [categoryRes, recommendRes, hotRes, latestRes].some(
      (result) => result.status === "rejected",
    );
    if (failed) {
      error.value = "首页数据加载失败，请稍后重试";
    }

    categories.value = payload(categoryRes.value, [])
      .filter((item) => !item.parent_id)
      .slice(0, 8);
    recommended.value = payload(recommendRes.value, []);
    hotSites.value = payload(hotRes.value, []);
    latestSites.value = payload(latestRes.value, []);
  } catch {
    error.value = "首页数据加载失败，请稍后重试";
  } finally {
    loading.value = false;
  }
}

onMounted(loadHome);
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: linear-gradient(180deg, #ffffff 0%, #ffffff 45%, #fffaf8 100%);
}

.home-main {
  display: grid;
  gap: 0;
}

.home-state {
  width: min(var(--container), calc(100% - 40px));
  margin: 80px auto;
}

@media (max-width: 768px) {
  .home-state {
    width: min(100% - 28px, var(--container));
    margin: 56px auto;
  }
}
</style>
